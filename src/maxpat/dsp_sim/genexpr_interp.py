"""GenExpr codebox interpreter (Q35, quick 261021-urs).

Runs the text of a gen~ codebox offline, sample by sample, so the codebox
smoke test (``smoke.py``) can look for NaN, runaway peaks and latched
feedback before MAX ever opens the patch.

Pipeline::

    mask(code)                       Q22 genexpr_parse: comments and string
                                     contents blanked, offsets preserved
      -> lexer                       NUMBER / IDENT / STRING / operators
      -> parser                      recursive descent for statements,
                                     Pratt for expressions -> small AST
      -> parse_codebox()             static checks: declarations, assignment
                                     targets, constant-name warnings
      -> Codebox.build(params=...)   resolver: every name becomes a constant,
                                     a slot or a built-in; Params are bound
                                     as constants for this corner; constant
                                     subtrees fold; every node compiles ONCE
                                     into a nested Python closure that reads
                                     and writes one flat list of float slots
      -> Program.run(inputs, n)      per-sample loop over the statement
                                     closures

This is an AST evaluator. No Python source text is generated, and nothing is
ever evaluated as a string: there is no eval, exec, compile or __import__
anywhere in this module (tests/dsp_sim/test_smoke.py pins this with an AST
scan). Codebox text can only select closures from the fixed operator and
built-in tables below.

Every construct outside the supported subset, every syntax error and every
unknown name raises :class:`Unsupported`, never another exception type, so a
caller can always report "unsupported" instead of a pass.

Semantics (tags carried over from 261021-urs-RESEARCH.md):

==========================  ==================================================
Construct                   Behaviour
==========================  ==================================================
numbers                     float64 throughout; ``1``, ``1.``, ``.5``, ``1e-1``
``in1..inN``                read-only input slots (assigning one is
                            Unsupported)
``out1..outN``              reset to 0.0 at the start of every sample
locals                      any other assigned name; reset to 0.0 every sample
History                     persists across samples; sequential: a read before
                            the assignment sees the previous sample, a read
                            after it sees the new value [ASSUMED, A5; genrun
                            makes the same assumption]
Param                       bound as a constant per corner, so Param-only
                            subexpressions fold (as gen hoists them);
                            ``Param p;`` defaults to 0.0; a non-literal
                            default is Unsupported
constants                   ``e pi twopi halfpi invpi ln2 ln10 log10e log2e
                            sqrt2 sqrt1_2 degtorad radtodeg phi`` plus the
                            MAX-confirmed uppercase ``PI TWOPI HALFPI``;
                            assigning to one is ignored (the constant wins,
                            as in MAX) and adds a warning
``samplerate``              the build samplerate, a constant
``/``                       0.0 when the divisor is 0 (genlib safediv)
                            [ASSUMED, A4]
``%``                       ``math.fmod`` (C sign), 0.0 for a zero divisor
                            [ASSUMED, A4]
comparisons ``&& ||``       both sides evaluated, result 1.0 / 0.0 [ASSUMED]
``c ? a : b``               all three evaluated (gen switch semantics)
``if / else``               only the taken branch's statements run; a
                            stateful call inside the untaken branch therefore
                            differs from gen, which executes both branches
math domain errors          a ValueError becomes nan (log/log10/log2 of 0 give
                            -inf); an OverflowError becomes +-inf; no numeric
                            Python exception escapes ``Program.run``
``wrap / fold``             1 argument (range 0..1) or 3; ``hi == lo`` returns
                            ``lo``; ``lo > hi`` is swapped [ASSUMED, A4]
==========================  ==================================================

Not supported (Unsupported): ``while``, ``return``, ``break``, ``continue``,
user functions, ``else if`` (nest ``else { if ... }``), brace-less if/else,
``!``, ``++``/``--``, bitwise operators, ``[]``, ``@`` attributes,
multi-assignment ``a, b = ...``, chained ``a = b = c``, keyword arguments in
calls, declarations after a statement or inside a block, and every Gen
operator the interpreter does not implement. In this build, for loops,
Delay / Data / Buffer and the stateful built-ins are still Unsupported.
"""

from __future__ import annotations

import math
import operator
import re
from dataclasses import dataclass, field

import numpy as np

from src.maxpat.genexpr_parse import CONSTANTS, io_counts, mask, parse_params

__all__ = [
    "GEN_CONSTANTS",
    "LOOP_CAP",
    "STATE_CAP",
    "Codebox",
    "Program",
    "Unsupported",
    "parse_codebox",
]


# ===========================================================================
# Errors, constants, caps
# ===========================================================================


class Unsupported(Exception):
    """A construct, name or syntax the interpreter does not run.

    ``construct`` names it; ``line`` is the 1-based codebox line or None.
    """

    def __init__(self, construct: str, line: int | None = None):
        self.construct = construct
        self.line = line
        super().__init__(construct, line)

    def __str__(self) -> str:
        if self.line is None:
            return f"unsupported: {self.construct}"
        return f"unsupported: {self.construct} (line {self.line})"


_LOWER_CONSTANTS = {
    "e": math.e,
    "pi": math.pi,
    "twopi": 2 * math.pi,
    "halfpi": math.pi / 2,
    "invpi": 1 / math.pi,
    "ln2": math.log(2.0),
    "ln10": math.log(10.0),
    "log10e": math.log10(math.e),
    "log2e": math.log2(math.e),
    "sqrt2": math.sqrt(2.0),
    "sqrt1_2": math.sqrt(0.5),
    "degtorad": math.pi / 180.0,
    "radtodeg": 180.0 / math.pi,
}
assert set(_LOWER_CONSTANTS) == set(CONSTANTS)

# Q22's 13 lowercase names, phi (in the installed Gen refpage list) and the
# uppercase PI / TWOPI / HALFPI used by MAX-confirmed shipped codeboxes.
# TWOPI and HALFPI use the exact expressions genrun.py uses, for parity.
GEN_CONSTANTS: dict[str, float] = {
    **_LOWER_CONSTANTS,
    "phi": (1.0 + math.sqrt(5.0)) / 2.0,
    "PI": math.pi,
    "TWOPI": 2 * math.pi,
    "HALFPI": math.pi / 2,
}

LOOP_CAP = 100_000          # for-loop iterations per loop per sample
STATE_CAP = 50_000_000      # total Delay + Data + Buffer samples

_MAX_DEPTH = 200            # expression nesting (closure depth) limit
_INF = float("inf")
_NAN = float("nan")
_DECL_TYPES = ("Param", "History", "Delay", "Buffer", "Data")


# ===========================================================================
# Lexer
# ===========================================================================

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
   |(?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
   |(?P<ident>[A-Za-z_]\w*)
   |(?P<str>"[^"]*")
   |(?P<bad>\+\+|--|!(?!=)|&(?!&)|\|(?!\|)|[\[\]@^~\#$\\'"`])
   |(?P<op>\+=|-=|\*=|/=|==|!=|<=|>=|&&|\|\||[-+*/%<>=?:(){},;.])
    """,
    re.X,
)

_BAD_NAMES = {
    "++": "'++' operator",
    "--": "'--' operator",
    "!": "'!' operator",
    "&": "bitwise '&' operator",
    "|": "bitwise '|' operator",
    "^": "bitwise '^' operator",
    "~": "bitwise '~' operator",
    "[": "'[' indexing",
    "]": "']' indexing",
    "@": "'@' attribute",
    '"': "unterminated string",
}


@dataclass(frozen=True, slots=True)
class _Tok:
    kind: str   # num | ident | str | op | eof
    text: str
    off: int


def _line_of(code: str, off: int) -> int:
    return code.count("\n", 0, off) + 1


def _lex(code: str) -> list[_Tok]:
    m_code = mask(code)
    toks: list[_Tok] = []
    pos = 0
    n = len(m_code)
    while pos < n:
        m = _TOKEN_RE.match(m_code, pos)
        if m is None:
            raise Unsupported(
                f"unexpected character {m_code[pos]!r}", _line_of(code, pos)
            )
        kind = m.lastgroup
        text = m.group()
        if kind == "bad":
            raise Unsupported(
                _BAD_NAMES.get(text, f"unexpected character {text!r}"),
                _line_of(code, pos),
            )
        if kind == "str":
            # mask blanks string contents: slice the ORIGINAL code.
            toks.append(_Tok("str", code[m.start() + 1:m.end() - 1], pos))
        elif kind != "ws":
            toks.append(_Tok(kind, text, pos))
        pos = m.end()
    toks.append(_Tok("eof", "", n))
    return toks


# ===========================================================================
# AST
# ===========================================================================


@dataclass(frozen=True, slots=True)
class Num:
    value: float
    off: int


@dataclass(frozen=True, slots=True)
class Str:
    value: str
    off: int


@dataclass(frozen=True, slots=True)
class Name:
    name: str
    off: int


@dataclass(frozen=True, slots=True)
class Unary:
    op: str
    a: object
    off: int


@dataclass(frozen=True, slots=True)
class Bin:
    op: str
    a: object
    b: object
    off: int


@dataclass(frozen=True, slots=True)
class Tern:
    c: object
    a: object
    b: object
    off: int


@dataclass(frozen=True, slots=True)
class Call:
    name: str
    args: tuple
    off: int


@dataclass(frozen=True, slots=True)
class Method:
    obj: str
    method: str
    args: tuple
    off: int


@dataclass(frozen=True, slots=True)
class Decl:
    dtype: str
    name: str
    args: tuple
    kwargs: tuple   # ((key, expr), ...)
    off: int


@dataclass(frozen=True, slots=True)
class Assign:
    name: str
    op: str         # = += -= *= /=
    expr: object
    off: int


@dataclass(frozen=True, slots=True)
class ExprStmt:
    expr: object
    off: int


@dataclass(frozen=True, slots=True)
class If:
    cond: object
    then: tuple
    els: tuple | None
    off: int


@dataclass(frozen=True, slots=True)
class For:
    init: Assign
    cond: object
    step: Assign
    body: tuple
    off: int


_ASSIGN_OPS = ("=", "+=", "-=", "*=", "/=")
_BIN_PREC = {
    "||": 1, "&&": 2,
    "==": 3, "!=": 3,
    "<": 4, ">": 4, "<=": 4, ">=": 4,
    "+": 5, "-": 5,
    "*": 6, "/": 6, "%": 6,
}
_STMT_KEYWORDS = (
    "while", "do", "return", "break", "continue", "switch", "case",
    "function", "require",
)


# ===========================================================================
# Parser
# ===========================================================================


class _Parser:
    def __init__(self, code: str):
        self.code = code
        self.toks = _lex(code)
        self.i = 0
        self.for_depth = 0
        self.seen_stmt = False

    # -- token helpers ------------------------------------------------------

    def err(self, construct: str, off: int) -> Unsupported:
        return Unsupported(construct, _line_of(self.code, off))

    def peek(self, k: int = 0) -> _Tok:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def advance(self) -> _Tok:
        t = self.toks[self.i]
        if t.kind != "eof":
            self.i += 1
        return t

    def is_op(self, text: str, k: int = 0) -> bool:
        t = self.peek(k)
        return t.kind == "op" and t.text == text

    def expect(self, text: str, what: str) -> _Tok:
        t = self.peek()
        if t.kind == "op" and t.text == text:
            return self.advance()
        found = t.text if t.kind != "eof" else "end of code"
        raise self.err(f"expected '{text}' {what}, found {found!r}", t.off)

    # -- statements ---------------------------------------------------------

    def program(self) -> list:
        out: list = []
        while self.peek().kind != "eof":
            out.extend(self.statement(top=True))
        return out

    def statement(self, top: bool) -> list:
        t = self.peek()
        if t.kind == "op" and t.text == ";":
            self.advance()
            return []
        if t.kind == "op" and t.text == "{":
            raise self.err("bare '{' block", t.off)
        if t.kind == "ident":
            w = t.text
            if w in _DECL_TYPES and self.peek(1).kind == "ident":
                if not top:
                    raise self.err(f"{w} declaration inside a block", t.off)
                if self.seen_stmt:
                    raise self.err(
                        f"{w} declaration after a statement (gen~ needs every "
                        "declaration first)",
                        t.off,
                    )
                return self.decl()
            if w == "if":
                self.seen_stmt = True
                return [self.if_stmt()]
            if w == "else":
                raise self.err("'else' without 'if'", t.off)
            if w == "for":
                self.seen_stmt = True
                return [self.for_stmt()]
            if w in _STMT_KEYWORDS:
                raise self.err(f"'{w}' statement", t.off)
        self.seen_stmt = True
        s = self.assign_or_expr()
        nt = self.peek()
        if nt.kind == "op":
            if nt.text == ";":
                self.advance()
                return [s]
            if nt.text == "{":
                raise self.err("user function definition", nt.off)
            if nt.text == ",":
                raise self.err("multi-assignment 'a, b = ...'", nt.off)
            if nt.text in _ASSIGN_OPS:
                raise self.err("chained assignment 'a = b = c'", nt.off)
        found = nt.text if nt.kind != "eof" else "end of code"
        raise self.err(f"missing ';' (found {found!r})", nt.off)

    def assign_or_expr(self):
        t = self.peek()
        t1 = self.peek(1)
        if t.kind == "ident" and t1.kind == "op" and t1.text in _ASSIGN_OPS:
            self.advance()
            self.advance()
            return Assign(t.text, t1.text, self.expr(), t.off)
        return ExprStmt(self.expr(), t.off)

    def assign_only(self, what: str) -> Assign:
        t = self.peek()
        s = self.assign_or_expr()
        if not isinstance(s, Assign):
            raise self.err(
                f"for loop {what} must be an assignment "
                "('for (i = 0; i < N; i += 1)')",
                t.off,
            )
        return s

    def block(self, what: str) -> tuple:
        t = self.peek()
        if not (t.kind == "op" and t.text == "{"):
            raise self.err(f"brace-less {what} body", t.off)
        self.advance()
        out: list = []
        while not self.is_op("}"):
            if self.peek().kind == "eof":
                raise self.err(f"missing '}}' closing the {what} body", t.off)
            out.extend(self.statement(top=False))
        self.advance()
        return tuple(out)

    def if_stmt(self) -> If:
        t = self.advance()
        self.expect("(", "after 'if'")
        cond = self.expr()
        self.expect(")", "closing the if condition")
        then = self.block("if")
        els = None
        nt = self.peek()
        if nt.kind == "ident" and nt.text == "else":
            self.advance()
            n2 = self.peek()
            if n2.kind == "ident" and n2.text == "if":
                raise self.err("'else if' (nest 'else { if ... }')", n2.off)
            els = self.block("else")
        return If(cond, then, els, t.off)

    def for_stmt(self) -> For:
        t = self.advance()
        if self.for_depth:
            raise self.err("nested for loop", t.off)
        self.expect("(", "after 'for'")
        init = self.assign_only("init")
        self.expect(";", "after the for init")
        cond = self.expr()
        self.expect(";", "after the for condition")
        step = self.assign_only("step")
        self.expect(")", "closing the for header")
        self.for_depth += 1
        try:
            body = self.block("for")
        finally:
            self.for_depth -= 1
        return For(init, cond, step, body, t.off)

    def decl(self) -> list:
        dt = self.advance().text
        items: list = []
        while True:
            nt = self.advance()
            if nt.kind != "ident":
                raise self.err(f"expected a name in the {dt} declaration", nt.off)
            args: tuple = ()
            kwargs: tuple = ()
            if self.is_op("("):
                self.advance()
                args, kwargs = self.arglist(allow_kw=True)
            items.append(Decl(dt, nt.text, args, kwargs, nt.off))
            if self.is_op(","):
                self.advance()
                continue
            break
        self.expect(";", f"after the {dt} declaration")
        return items

    def arglist(self, allow_kw: bool) -> tuple:
        """Parse arguments after '(' up to and including ')'."""
        args: list = []
        kwargs: list = []
        if self.is_op(")"):
            self.advance()
            return tuple(args), tuple(kwargs)
        while True:
            t = self.peek()
            if t.kind == "ident" and self.is_op("=", 1):
                if not allow_kw:
                    raise self.err(f"keyword argument '{t.text}=' in a call", t.off)
                self.advance()
                self.advance()
                kwargs.append((t.text, self.expr()))
            else:
                if kwargs:
                    raise self.err("positional argument after a keyword", t.off)
                args.append(self.expr())
            if self.is_op(","):
                self.advance()
                continue
            self.expect(")", "closing the argument list")
            return tuple(args), tuple(kwargs)

    # -- expressions (Pratt) -------------------------------------------------

    def expr(self):
        return self.ternary()

    def ternary(self):
        c = self.binary(1)
        if self.is_op("?"):
            q = self.advance()
            a = self.ternary()
            self.expect(":", "in the ternary")
            b = self.ternary()
            return Tern(c, a, b, q.off)
        return c

    def binary(self, min_prec: int):
        left = self.unary()
        while True:
            t = self.peek()
            if t.kind != "op" or t.text not in _BIN_PREC:
                return left
            prec = _BIN_PREC[t.text]
            if prec < min_prec:
                return left
            self.advance()
            right = self.binary(prec + 1)
            left = Bin(t.text, left, right, t.off)

    def unary(self):
        t = self.peek()
        if t.kind == "op" and t.text in ("-", "+"):
            self.advance()
            return Unary(t.text, self.unary(), t.off)
        return self.primary()

    def primary(self):
        t = self.advance()
        if t.kind == "num":
            return Num(float(t.text), t.off)
        if t.kind == "str":
            return Str(t.text, t.off)
        if t.kind == "op" and t.text == "(":
            e = self.expr()
            self.expect(")", "closing '('")
            return e
        if t.kind == "ident":
            if self.is_op("("):
                self.advance()
                args, _kw = self.arglist(allow_kw=False)
                return Call(t.text, args, t.off)
            if self.is_op("."):
                self.advance()
                m = self.advance()
                if m.kind != "ident":
                    raise self.err(f"expected a method name after '{t.text}.'", m.off)
                if not self.is_op("("):
                    raise self.err(f"member access '{t.text}.{m.text}' without a call", m.off)
                self.advance()
                args, _kw = self.arglist(allow_kw=False)
                return Method(t.text, m.text, args, m.off)
            return Name(t.text, t.off)
        found = t.text if t.kind != "eof" else "end of code"
        raise self.err(f"unexpected {found!r} in an expression", t.off)


# ===========================================================================
# Static walk helpers
# ===========================================================================


def _expr_depth(node) -> int:
    if isinstance(node, (Num, Str, Name)):
        return 1
    if isinstance(node, Unary):
        return 1 + _expr_depth(node.a)
    if isinstance(node, Bin):
        return 1 + max(_expr_depth(node.a), _expr_depth(node.b))
    if isinstance(node, Tern):
        return 1 + max(_expr_depth(node.c), _expr_depth(node.a), _expr_depth(node.b))
    if isinstance(node, (Call, Method)):
        return 1 + max((_expr_depth(a) for a in node.args), default=0)
    return 1


def _walk_stmts(stmts):
    """Yield every statement, recursing into if/else and for bodies."""
    for s in stmts:
        yield s
        if isinstance(s, If):
            yield from _walk_stmts(s.then)
            if s.els:
                yield from _walk_stmts(s.els)
        elif isinstance(s, For):
            yield s.init
            yield s.step
            yield from _walk_stmts(s.body)


def _stmt_exprs(s):
    if isinstance(s, (Assign, ExprStmt)):
        return (s.expr,)
    if isinstance(s, If):
        return (s.cond,)
    if isinstance(s, For):
        return (s.cond,)
    return ()


_IN_NAME = re.compile(r"in(\d+)$")
_OUT_NAME = re.compile(r"out(\d+)$")


# ===========================================================================
# Codebox
# ===========================================================================


@dataclass
class Codebox:
    """A parsed codebox. ``build()`` compiles one Program per Param corner."""

    code: str
    n_in: int
    n_out: int
    params: list            # [{name, default, min, max}], defaults resolved
    warnings: list
    decls: tuple
    body: tuple
    _locals: tuple = field(default=(), repr=False)
    _ignored: frozenset = field(default=frozenset(), repr=False)

    def build(
        self,
        *,
        params: dict | None = None,
        samplerate: float = 44100.0,
        seed: int = 1,
        buffers: dict | None = None,
    ) -> "Program":
        """Compile this codebox for one Param corner.

        ``params`` overrides Param values by name (a name that is not a
        declared Param raises ValueError). Raises Unsupported for anything the
        interpreter cannot run.
        """
        return _Builder(self, params or {}, float(samplerate), seed, buffers or {}).program()


def parse_codebox(code: str) -> Codebox:
    """Parse codebox text. Raises Unsupported on any syntax outside the subset."""
    if not isinstance(code, str):
        raise Unsupported("codebox code is not text")
    try:
        stmts = _Parser(code).program()
    except RecursionError:
        raise Unsupported("expression nesting too deep") from None

    decls = tuple(s for s in stmts if isinstance(s, Decl))
    body = tuple(s for s in stmts if not isinstance(s, Decl))

    def err(construct, off):
        return Unsupported(construct, _line_of(code, off))

    # Expression depth bound (closure nesting must stay far below the
    # Python recursion limit).
    for s in _walk_stmts(body):
        for e in _stmt_exprs(s):
            if _expr_depth(e) > _MAX_DEPTH:
                raise err("expression nesting too deep", s.off)
    for d in decls:
        for e in list(d.args) + [v for _k, v in d.kwargs]:
            if _expr_depth(e) > _MAX_DEPTH:
                raise err("expression nesting too deep", d.off)

    # Declarations.
    declared: dict[str, Decl] = {}
    for d in decls:
        if d.name in declared:
            raise err(f"duplicate declaration of '{d.name}'", d.off)
        if d.name in GEN_CONSTANTS or d.name == "samplerate":
            raise err(f"declaration shadows the built-in name '{d.name}'", d.off)
        if _IN_NAME.match(d.name) or _OUT_NAME.match(d.name):
            raise err(f"declaration of the I/O name '{d.name}'", d.off)
        declared[d.name] = d

    # Params: parse_params is the single source of default/min/max.
    by_name = {p["name"]: p for p in parse_params(code)}
    params: list = []
    for d in decls:
        if d.dtype != "Param":
            continue
        p = dict(by_name.get(d.name, {"name": d.name, "default": None, "min": None, "max": None}))
        if p["default"] is None:
            if d.args:
                raise err(f"non-literal default for Param '{d.name}'", d.off)
            p["default"] = 0.0
        params.append(p)

    # Assignment targets.
    warnings: list = []
    locals_: list = []
    ignored: set = set()
    seen_local: set = set()
    for s in _walk_stmts(body):
        if not isinstance(s, Assign):
            continue
        name = s.name
        if name in GEN_CONSTANTS:
            warnings.append(
                f"line {_line_of(code, s.off)}: assignment to the built-in "
                f"constant '{name}' is ignored (the constant wins)"
            )
            ignored.add(id(s))
            continue
        if name == "samplerate":
            raise err("assignment to 'samplerate'", s.off)
        if _IN_NAME.match(name):
            raise err(f"assignment to the input '{name}'", s.off)
        d = declared.get(name)
        if d is not None:
            if d.dtype == "Param":
                raise err(f"assignment to Param '{name}'", s.off)
            if d.dtype != "History":
                raise err(f"assignment to the {d.dtype} '{name}'", s.off)
            continue
        if _OUT_NAME.match(name):
            continue
        if name not in seen_local:
            seen_local.add(name)
            locals_.append(name)

    n_in, n_out = io_counts(code)
    return Codebox(
        code=code,
        n_in=n_in,
        n_out=n_out,
        params=params,
        warnings=warnings,
        decls=decls,
        body=body,
        _locals=tuple(locals_),
        _ignored=frozenset(ignored),
    )


# ===========================================================================
# Pure built-ins (never raise on numeric input)
# ===========================================================================


def _safediv(a: float, b: float) -> float:
    return a / b if b != 0.0 else 0.0


def _fmod(a: float, b: float) -> float:
    if b == 0.0:
        return 0.0
    try:
        return math.fmod(a, b)
    except ValueError:
        return _NAN


def _exp(x):
    try:
        return math.exp(x)
    except OverflowError:
        return _INF


def _exp2(x):
    try:
        return math.exp2(x)
    except OverflowError:
        return _INF


def _mk_log(fn):
    def f(x):
        try:
            return fn(x)
        except ValueError:
            return -_INF if x == 0.0 else _NAN
    return f


_log = _mk_log(math.log)
_log10 = _mk_log(math.log10)
_log2 = _mk_log(math.log2)


def _mk_nan_on_value_error(fn):
    def f(x):
        try:
            return fn(x)
        except ValueError:
            return _NAN
    return f


_sqrt = _mk_nan_on_value_error(math.sqrt)
_sin = _mk_nan_on_value_error(math.sin)
_cos = _mk_nan_on_value_error(math.cos)
_tan = _mk_nan_on_value_error(math.tan)
_asin = _mk_nan_on_value_error(math.asin)
_acos = _mk_nan_on_value_error(math.acos)


def _sinh(x):
    try:
        return math.sinh(x)
    except OverflowError:
        return math.copysign(_INF, x)


def _cosh(x):
    try:
        return math.cosh(x)
    except OverflowError:
        return _INF


def _pow(x, y):
    try:
        return math.pow(x, y)
    except ValueError:
        return _NAN
    except OverflowError:
        neg = x < 0.0 and float(y).is_integer() and int(y) % 2 == 1
        return -_INF if neg else _INF


def _atan2(y, x):
    try:
        return math.atan2(y, x)
    except ValueError:
        return _NAN


def _mk_round(fn):
    def f(x):
        try:
            return float(fn(x))
        except (ValueError, OverflowError):
            return x   # nan stays nan, +-inf stays +-inf
    return f


_floor = _mk_round(math.floor)
_ceil = _mk_round(math.ceil)
_trunc = _mk_round(math.trunc)


def _fract(x):
    return x - _floor(x)


def _sign(x):
    if x > 0.0:
        return 1.0
    if x < 0.0:
        return -1.0
    return x * 0.0 if x != x else 0.0


def _clamp(x, lo, hi):
    return min(max(x, lo), hi)


def _mix(a, b, t):
    return a + (b - a) * t


def _wrap(x, lo=0.0, hi=1.0):
    if lo > hi:
        lo, hi = hi, lo
    r = hi - lo
    if r == 0.0:
        return lo
    try:
        y = math.fmod(x - lo, r)
    except ValueError:
        return _NAN
    if y < 0.0:
        y += r
    return lo + y


def _fold(x, lo=0.0, hi=1.0):
    if lo > hi:
        lo, hi = hi, lo
    r = hi - lo
    if r == 0.0:
        return lo
    r2 = 2.0 * r
    try:
        y = math.fmod(x - lo, r2)
    except ValueError:
        return _NAN
    if y < 0.0:
        y += r2
    if y > r:
        y = r2 - y
    return lo + y


def _fixnan(x):
    return 0.0 if x != x else x


def _fixdenorm(x):
    return 0.0 if 0.0 < abs(x) < 2.2250738585072014e-308 else x


# name -> (function, allowed arg counts). Functions are pure: same args, same
# result, so all-constant calls fold at build time.
_PURE: dict[str, tuple] = {
    "abs": (abs, (1,)),
    "min": (min, (2,)),
    "max": (max, (2,)),
    "clamp": (_clamp, (3,)),
    "clip": (_clamp, (3,)),
    "exp": (_exp, (1,)),
    "exp2": (_exp2, (1,)),
    "log": (_log, (1,)),
    "log10": (_log10, (1,)),
    "log2": (_log2, (1,)),
    "pow": (_pow, (2,)),
    "sqrt": (_sqrt, (1,)),
    "tanh": (math.tanh, (1,)),
    "sinh": (_sinh, (1,)),
    "cosh": (_cosh, (1,)),
    "sin": (_sin, (1,)),
    "cos": (_cos, (1,)),
    "tan": (_tan, (1,)),
    "asin": (_asin, (1,)),
    "acos": (_acos, (1,)),
    "atan": (math.atan, (1,)),
    "atan2": (_atan2, (2,)),
    "floor": (_floor, (1,)),
    "ceil": (_ceil, (1,)),
    "trunc": (_trunc, (1,)),
    "fract": (_fract, (1,)),
    "sign": (_sign, (1,)),
    "mix": (_mix, (3,)),
    "wrap": (_wrap, (1, 3)),
    "fold": (_fold, (1, 3)),
    "fixnan": (_fixnan, (1,)),
    "fixdenorm": (_fixdenorm, (1,)),
    # mstosamps / sampstoms are bound to the build samplerate in _Builder.
    "mstosamps": (None, (1,)),
    "sampstoms": (None, (1,)),
}

# Operators that are part of Gen but come in Task 2 of 261021-urs.
_STATEFUL_LATER = frozenset({
    "peek", "poke", "dim", "channels", "noise", "phasor", "latch", "dcblock",
    "cycle", "triangle", "selector", "mc_channel", "mc_channelcount",
})


# ===========================================================================
# Closure compiler
# ===========================================================================
#
# compile_expr returns one of three shapes:
#   ("c", value)   a folded constant
#   ("s", index)   a plain slot read
#   ("f", fn)      a closure fn(env) -> float
# Shapes let the binary operators and assignments specialise their closures
# (slot op const, const op slot, slot op slot) and skip a call per node.

_C, _S, _F = "c", "s", "f"


def _as_fn(ce):
    kind, x = ce
    if kind == _F:
        return x
    if kind == _S:
        return operator.itemgetter(x)
    return lambda env, _v=x: _v


def _mk_add(ka, a, kb, b):
    if ka == _S:
        if kb == _S:
            return lambda env: env[a] + env[b]
        if kb == _C:
            return lambda env: env[a] + b
        return lambda env: env[a] + b(env)
    if ka == _C:
        if kb == _S:
            return lambda env: a + env[b]
        return lambda env: a + b(env)
    if kb == _S:
        return lambda env: a(env) + env[b]
    if kb == _C:
        return lambda env: a(env) + b
    return lambda env: a(env) + b(env)


def _mk_sub(ka, a, kb, b):
    if ka == _S:
        if kb == _S:
            return lambda env: env[a] - env[b]
        if kb == _C:
            return lambda env: env[a] - b
        return lambda env: env[a] - b(env)
    if ka == _C:
        if kb == _S:
            return lambda env: a - env[b]
        return lambda env: a - b(env)
    if kb == _S:
        return lambda env: a(env) - env[b]
    if kb == _C:
        return lambda env: a(env) - b
    return lambda env: a(env) - b(env)


def _mk_mul(ka, a, kb, b):
    if ka == _S:
        if kb == _S:
            return lambda env: env[a] * env[b]
        if kb == _C:
            return lambda env: env[a] * b
        return lambda env: env[a] * b(env)
    if ka == _C:
        if kb == _S:
            return lambda env: a * env[b]
        return lambda env: a * b(env)
    if kb == _S:
        return lambda env: a(env) * env[b]
    if kb == _C:
        return lambda env: a(env) * b
    return lambda env: a(env) * b(env)


def _mk_div(ka, a, kb, b):
    if kb == _C:
        if b != 0.0:
            if ka == _S:
                return lambda env: env[a] / b
            fa = _as_fn((ka, a))
            return lambda env: fa(env) / b
        fa = _as_fn((ka, a))

        def zero(env):
            fa(env)   # evaluated for its side effects; safediv gives 0
            return 0.0
        return zero
    fa = _as_fn((ka, a))
    fb = _as_fn((kb, b))

    def div(env):
        n = fa(env)
        d = fb(env)
        return n / d if d != 0.0 else 0.0
    return div


def _mk_generic2(fn, ka, a, kb, b):
    fa = _as_fn((ka, a))
    fb = _as_fn((kb, b))
    return lambda env: fn(fa(env), fb(env))


def _cmp_fn(op):
    if op == "<":
        return lambda x, y: 1.0 if x < y else 0.0
    if op == ">":
        return lambda x, y: 1.0 if x > y else 0.0
    if op == "<=":
        return lambda x, y: 1.0 if x <= y else 0.0
    if op == ">=":
        return lambda x, y: 1.0 if x >= y else 0.0
    if op == "==":
        return lambda x, y: 1.0 if x == y else 0.0
    if op == "!=":
        return lambda x, y: 1.0 if x != y else 0.0
    if op == "&&":
        return lambda x, y: 1.0 if (x != 0.0 and y != 0.0) else 0.0
    if op == "||":
        return lambda x, y: 1.0 if (x != 0.0 or y != 0.0) else 0.0
    raise AssertionError(op)


def _mk_cmp(op, ka, a, kb, b):
    """Comparison / logic closure; both sides always evaluated, left first."""
    fa = _as_fn((ka, a))
    fb = _as_fn((kb, b))
    if op == "<":
        if ka == _S and kb == _C:
            return lambda env: 1.0 if env[a] < b else 0.0
        return lambda env: 1.0 if fa(env) < fb(env) else 0.0
    if op == ">":
        if ka == _S and kb == _C:
            return lambda env: 1.0 if env[a] > b else 0.0
        return lambda env: 1.0 if fa(env) > fb(env) else 0.0
    if op == "<=":
        return lambda env: 1.0 if fa(env) <= fb(env) else 0.0
    if op == ">=":
        if ka == _S and kb == _C:
            return lambda env: 1.0 if env[a] >= b else 0.0
        return lambda env: 1.0 if fa(env) >= fb(env) else 0.0
    if op == "==":
        return lambda env: 1.0 if fa(env) == fb(env) else 0.0
    if op == "!=":
        return lambda env: 1.0 if fa(env) != fb(env) else 0.0

    if op == "&&":
        def land(env):
            x = fa(env)
            y = fb(env)
            return 1.0 if (x != 0.0 and y != 0.0) else 0.0
        return land

    def lor(env):
        x = fa(env)
        y = fb(env)
        return 1.0 if (x != 0.0 or y != 0.0) else 0.0
    return lor


_FOLD_BIN = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": _safediv,
    "%": _fmod,
}


def _mk_assign(t, ce):
    kind, x = ce
    if kind == _C:
        def s(env):
            env[t] = x
    elif kind == _S:
        def s(env):
            env[t] = env[x]
    else:
        def s(env):
            env[t] = x(env)
    return s


def _mk_seq(stmts: tuple):
    if len(stmts) == 1:
        return stmts[0]

    def seq(env):
        for st in stmts:
            st(env)
    return seq


class _Builder:
    def __init__(self, cb: Codebox, params: dict, samplerate: float, seed, buffers: dict):
        self.cb = cb
        self.code = cb.code
        self.samplerate = samplerate
        self.seed = seed
        self.buffers = buffers
        pvals = {p["name"]: float(p["default"]) for p in cb.params}
        for k, v in params.items():
            if k not in pvals:
                raise ValueError(f"not a declared Param: {k!r}")
            pvals[k] = float(v)
        self.pvals = pvals
        self.declared = {d.name: d for d in cb.decls}

        # Slot layout: inputs | outputs | locals | history.
        self.slots: dict[str, int] = {}
        for k in range(cb.n_in):
            self.slots[f"in{k + 1}"] = k
        o_lo = cb.n_in
        for k in range(cb.n_out):
            self.slots[f"out{k + 1}"] = o_lo + k
        nxt = o_lo + cb.n_out
        for name in cb._locals:
            self.slots[name] = nxt
            nxt += 1
        self.out_range = (o_lo, o_lo + cb.n_out)
        self.reset_hi = nxt
        self.init: list = [0.0] * nxt
        self.post: list = []   # end-of-sample callbacks (Delay heads, Task 2)

    def err(self, construct, off):
        return Unsupported(construct, _line_of(self.code, off))

    # -- declarations ---------------------------------------------------------

    def _decls(self):
        for d in self.cb.decls:
            if d.dtype == "Param":
                continue
            if d.dtype == "History":
                if len(d.args) > 1 or d.kwargs:
                    raise self.err(f"History '{d.name}' takes one initial value", d.off)
                v = 0.0
                if d.args:
                    ce = self.expr(d.args[0])
                    if ce[0] != _C:
                        raise self.err(
                            f"non-constant initial value for History '{d.name}'", d.off
                        )
                    v = ce[1]
                self.slots[d.name] = len(self.init)
                self.init.append(float(v))
                continue
            raise self.err(f"{d.dtype} declaration '{d.name}'", d.off)

    # -- expressions ----------------------------------------------------------

    def expr(self, node):
        if isinstance(node, Num):
            return (_C, node.value)
        if isinstance(node, Name):
            return self.name(node)
        if isinstance(node, Unary):
            kind, x = self.expr(node.a)
            if node.op == "+":
                return (kind, x)
            if kind == _C:
                return (_C, -x)
            if kind == _S:
                return (_F, lambda env: -env[x])
            return (_F, lambda env: -x(env))
        if isinstance(node, Bin):
            return self.binop(node.op, self.expr(node.a), self.expr(node.b))
        if isinstance(node, Tern):
            c = self.expr(node.c)
            a = self.expr(node.a)
            b = self.expr(node.b)
            if c[0] == _C and a[0] == _C and b[0] == _C:
                return (_C, a[1] if c[1] != 0.0 else b[1])
            fc, fa, fb = _as_fn(c), _as_fn(a), _as_fn(b)

            def tern(env):
                cv = fc(env)
                av = fa(env)
                bv = fb(env)
                return av if cv != 0.0 else bv
            return (_F, tern)
        if isinstance(node, Call):
            return self.call(node)
        if isinstance(node, Method):
            return self.method(node)
        if isinstance(node, Str):
            raise self.err("string literal in an expression", node.off)
        raise self.err(f"expression {type(node).__name__}", getattr(node, "off", 0))

    def name(self, node: Name):
        n = node.name
        if n in GEN_CONSTANTS:
            return (_C, GEN_CONSTANTS[n])
        if n in self.pvals:
            return (_C, self.pvals[n])
        if n == "samplerate":
            return (_C, self.samplerate)
        if n in self.slots:
            return (_S, self.slots[n])
        d = self.declared.get(n)
        if d is not None:
            raise self.err(f"{d.dtype} '{n}' used as a value", node.off)
        if _OUT_NAME.match(n):
            raise self.err(f"output '{n}' read but never assigned", node.off)
        if _IN_NAME.match(n):
            raise self.err(f"unknown identifier: {n}", node.off)
        if n in _STATEFUL_LATER:
            raise self.err(f"Gen operator not implemented: {n}", node.off)
        raise self.err(f"unknown identifier: {n}", node.off)

    def binop(self, op, a, b):
        ka, xa = a
        kb, xb = b
        if ka == _C and kb == _C:
            if op in _FOLD_BIN:
                return (_C, _FOLD_BIN[op](xa, xb))
            return (_C, _cmp_fn(op)(xa, xb))
        if op == "+":
            return (_F, _mk_add(ka, xa, kb, xb))
        if op == "-":
            return (_F, _mk_sub(ka, xa, kb, xb))
        if op == "*":
            return (_F, _mk_mul(ka, xa, kb, xb))
        if op == "/":
            return (_F, _mk_div(ka, xa, kb, xb))
        if op == "%":
            return (_F, _mk_generic2(_fmod, ka, xa, kb, xb))
        return (_F, _mk_cmp(op, ka, xa, kb, xb))

    def call(self, node: Call):
        name = node.name
        nargs = len(node.args)
        if name in _PURE:
            fn, arities = _PURE[name]
            if nargs not in arities:
                want = " or ".join(str(a) for a in arities)
                raise self.err(
                    f"{name}() takes {want} argument(s), got {nargs}", node.off
                )
            if name == "mstosamps":
                sr = self.samplerate
                fn = lambda x, _sr=sr: x * _sr * 0.001  # noqa: E731
            elif name == "sampstoms":
                sr = self.samplerate
                fn = lambda x, _sr=sr: x * 1000.0 / _sr  # noqa: E731
            args = [self.expr(a) for a in node.args]
            if all(k == _C for k, _x in args):
                return (_C, fn(*[x for _k, x in args]))
            if nargs == 1:
                k, x = args[0]
                if k == _S:
                    return (_F, lambda env: fn(env[x]))
                return (_F, lambda env: fn(x(env)))
            fs = [_as_fn(a) for a in args]
            if nargs == 2:
                f0, f1 = fs
                return (_F, lambda env: fn(f0(env), f1(env)))
            f0, f1, f2 = fs
            return (_F, lambda env: fn(f0(env), f1(env), f2(env)))
        if name in _STATEFUL_LATER:
            raise self.err(f"Gen operator not implemented: {name}", node.off)
        raise self.err(f"unknown function: {name}", node.off)

    def method(self, node: Method):
        raise self.err(f"method call '{node.obj}.{node.method}()'", node.off)

    # -- statements -----------------------------------------------------------

    def stmts(self, stmts) -> list:
        out: list = []
        for s in stmts:
            out.extend(self.stmt(s))
        return out

    def stmt(self, s) -> list:
        if isinstance(s, Assign):
            if id(s) in self.cb._ignored:
                # Assignment to a built-in constant: ignored, but the right
                # side still runs for its side effects.
                ce = self.expr(s.expr)
                return [] if ce[0] != _F else [ce[1]]
            t = self.slots[s.name]
            value = self.expr(s.expr)
            if s.op != "=":
                value = self.binop(s.op[0], (_S, t), value)
            return [_mk_assign(t, value)]
        if isinstance(s, ExprStmt):
            ce = self.expr(s.expr)
            return [ce[1]] if ce[0] == _F else []
        if isinstance(s, If):
            c = self.expr(s.cond)
            then = tuple(self.stmts(s.then))
            els = tuple(self.stmts(s.els)) if s.els else ()
            if c[0] == _C:
                return list(then if c[1] != 0.0 else els)
            fc = _as_fn(c)
            if not then and not els:
                return [fc]
            fthen = _mk_seq(then) if then else None
            fels = _mk_seq(els) if els else None
            if fels is None:
                def if_(env):
                    if fc(env) != 0.0:
                        fthen(env)
            elif fthen is None:
                def if_(env):
                    if fc(env) == 0.0:
                        fels(env)
            else:
                def if_(env):
                    if fc(env) != 0.0:
                        fthen(env)
                    else:
                        fels(env)
            return [if_]
        if isinstance(s, For):
            raise self.err("for loop", s.off)
        raise self.err(f"statement {type(s).__name__}", getattr(s, "off", 0))

    def program(self) -> "Program":
        self._decls()
        stmts = tuple(self.stmts(self.cb.body))
        return Program(
            n_in=self.cb.n_in,
            n_out=self.cb.n_out,
            out_range=self.out_range,
            reset_hi=self.reset_hi,
            env=self.init,
            stmts=stmts,
            post=tuple(self.post),
        )


# ===========================================================================
# Program
# ===========================================================================


class Program:
    """A compiled codebox for one corner. State persists across ``run`` calls."""

    def __init__(self, *, n_in, n_out, out_range, reset_hi, env, stmts, post):
        self.n_in = n_in
        self.n_out = n_out
        self._out_range = out_range
        self._reset_hi = reset_hi
        self._env = list(env)
        self._stmts = stmts
        self._post = post

    def run(self, inputs, n_samples: int) -> list:
        """Run ``n_samples`` samples. ``inputs`` holds one array per inlet.

        Returns out1..outN as float64 numpy arrays.
        """
        n_samples = int(n_samples)
        if len(inputs) != self.n_in:
            raise ValueError(f"expected {self.n_in} input arrays, got {len(inputs)}")
        cols = []
        for k, x in enumerate(inputs):
            arr = np.asarray(x, dtype=float).ravel()
            if arr.size < n_samples:
                raise ValueError(f"input {k + 1} has {arr.size} samples, need {n_samples}")
            cols.append(arr[:n_samples].tolist())
        n_in = self.n_in
        reset_hi = self._reset_hi
        zeros = (0.0,) * (reset_hi - n_in)
        env = self._env
        stmts = self._stmts
        post = self._post
        o_lo, o_hi = self._out_range
        out: list = []
        append = out.append
        if n_in:
            rows = [tuple(r) + zeros for r in zip(*cols)]
            for n in range(n_samples):
                env[0:reset_hi] = rows[n]
                for st in stmts:
                    st(env)
                for p in post:
                    p()
                append(env[o_lo:o_hi])
        else:
            for n in range(n_samples):
                env[0:reset_hi] = zeros
                for st in stmts:
                    st(env)
                for p in post:
                    p()
                append(env[o_lo:o_hi])
        if self.n_out == 0:
            return []
        arr = np.array(out, dtype=float).reshape(n_samples, self.n_out)
        return [arr[:, k].copy() for k in range(self.n_out)]
