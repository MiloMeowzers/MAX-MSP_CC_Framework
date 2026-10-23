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
locals                      any other assigned name; reset to 0.0 every sample;
                            must be assigned on every path before being read
                            (checked at parse time; gen's 'not defined');
                            names first assigned inside an if/else or for
                            block are local to it
History                     persists across samples; sequential: a read before
                            the assignment sees the previous sample, a read
                            after it sees the new value [ASSUMED, A5; genrun
                            makes the same assumption]
Param                       bound as a constant per corner, so Param-only
                            subexpressions fold (as gen hoists them);
                            ``Param p;`` defaults to 0.0; a non-literal
                            default is Unsupported; default and overrides
                            clamped to [min, max] (gen param refpage:
                            'Incoming values out of range will be clamped';
                            initial-value clamp [ASSUMED for gen~, RNBO
                            genexpr_js clamps it])
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
``if / else``               only the taken branch's statements run. This is
                            the simulator's choice and is unconfirmed in MAX.
                            The Max 9.2 GenExpr guide ('Branching and
                            Looping'), RNBO genexpr_js (it emits an
                            IfStatement) and shipped Examples/gen such as
                            gen~.chopper_repeat point to conditional
                            execution, while genexpr-rules.md says both
                            branches always execute. A stateful call (noise,
                            phasor, cycle, latch, dcblock, poke, Delay write)
                            inside a branch therefore advances or writes only
                            when that branch runs. smoke reports each such
                            codebox with an INFO ``branch_state`` finding
math domain errors          a ValueError becomes nan (log/log10/log2 of 0 give
                            -inf); an OverflowError becomes +-inf; no numeric
                            Python exception escapes ``Program.run``
``wrap / fold``             1 argument (range 0..1) or 3; ``hi == lo`` returns
                            ``lo``; ``lo > hi`` is swapped [ASSUMED, A4]
``for``                     ``for (i = a; i <op> BOUND; i += s) { ... }``;
                            BOUND must fold to a constant at build time (a
                            Param bound folds per corner); more than LOOP_CAP
                            iterations in one sample raises Unsupported; a
                            nested for is Unsupported
``Delay d(N)``              ring of N+2 floats; ``d.write(x)`` stores at the
                            head (the last write in a sample wins);
                            ``d.read(t)`` clamps t to [1, N] and interpolates
                            linearly between taps floor(t) and floor(t)+1;
                            every head advances once at the end of the sample,
                            so a write-then-read in one sample still sees the
                            previous samples [Delay defaults per refpage:
                            interp linear, feedback 1; ring details ASSUMED]
``Data n(frames[, ch])``    zero-filled, one list per channel
``Buffer n("name")``        MAX's buffer~ contents are not available offline:
                            backed by 48000 frames x 1 channel of
                            0.25 * sin(2*pi*220*n/samplerate), resizable per
                            buffer~ name with ``buffers={name: (frames, ch)}``
``peek(buf, i[, ch])``      no interpolation, index floored [ASSUMED, A4];
                            an index or channel out of range (or a non-finite
                            index) gives 0.0 (refpage boundmode ignore)
``poke(buf, v, i[, ch])``   out of range writes nothing (refpage)
``dim / channels``          frame / channel count, constants
``noise()``                 one ``random.Random(seed)`` per Program; each call
                            returns ``-1 + 2 * rng.random()`` (genrun's
                            ``random.uniform(-1, 1)`` stream) [ASSUMED range]
``phasor(f[, reset])``      returns the current phase, then advances by
                            f/samplerate wrapped into [0, 1); a non-zero reset
                            sets the phase to 0 first
``cycle(f)``                sin(2*pi*phase) of an internal phase [ASSUMED]
``latch(x, c)``             holds while c == 0; initial value 0
``dcblock(x)``              y = x - x1 + 0.9997 * y1 (refpage GenExpr)
``triangle(p[, duty])``     pure; up to the duty point and back down
``selector(i, a, b, ...)``  floor(i); i <= 0 gives 0.0, i above the count
                            clamps to the last [ASSUMED]
``mc_channel(count)``       1.0 (one simulated channel)
==========================  ==================================================

Stateful built-ins keep one state cell per call site, created at build time.

``Codebox.lint`` holds build-time WARNs as (check, detail) pairs: ``tab_char``
(a tab anywhere in the code; the project's safe-construct rules say spaces
only), ``output_typo`` (a never-read local such as ``ou2`` or ``Out1`` that
looks like a misspelled output), and the genexpr-rules.md safe-construct
checks (261022-ud6 IN-01): ``loop_bound_param`` (a for bound reading a Param,
samplerate or vectorsize; the simulator folds it per corner but gen~ wants a
CONSTANT bound), ``hoist_alias`` (a Param-only statement reading a bare local
alias such as ``sr = samplerate;``) and ``implicit_channel`` (peek / poke
without the channel argument). ``Codebox.advisories``
holds build-time INFOs the same way: ``branch_state`` names each stateful call
or write inside an if/else body (see the ``if / else`` row); it never changes a
smoke verdict.

Not supported (Unsupported): ``while``, ``return``, ``break``, ``continue``,
user functions, ``else if`` (nest ``else { if ... }``), brace-less if/else,
``!``, ``++``/``--``, bitwise operators, ``[]``, ``@`` attributes,
multi-assignment ``a, b = ...``, chained ``a = b = c``, keyword arguments in
calls, declarations after a statement or inside a block, multi-tap Delay,
Delay methods other than read/write, more than STATE_CAP Delay/Data/Buffer
samples, and every name in GEN_OPERATOR_NAMES the interpreter does not
implement ("Gen operator not implemented"). Any other unknown call is
"unknown function"; any other unknown name is "unknown identifier".
"""

from __future__ import annotations

import math
import operator
import random
import re
from dataclasses import dataclass, field

import numpy as np

from src.maxpat.genexpr_parse import CONSTANTS, io_counts, mask, parse_params

__all__ = [
    "GEN_CONSTANTS",
    "GEN_OPERATOR_NAMES",
    "LOOP_CAP",
    "STATE_CAP",
    "Codebox",
    "Program",
    "Unsupported",
    "parse_codebox",
    "value_dependencies",
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

# Every `<c74object name='...'>` in the installed Gen refpages under
# /Applications/Max.app/Contents/Resources/C74/packages/Gen/docs/refpages/common
# and .../dsp, Max 9.2.0 (162 names, generated once at implementation time;
# the Max bundle is never read at runtime). A call to one of these that the
# interpreter does not implement is "Gen operator not implemented"; any
# other unknown call is "unknown function".
GEN_OPERATOR_NAMES = frozenset({
    "abs", "absdiff", "accum", "acos", "acosh", "add", "and", "asin", "asinh",
    "atan", "atan2", "atanh", "atodb", "bool", "buffer", "cartopol", "ceil",
    "change", "channels", "clamp", "clip", "constant", "cos", "cosh",
    "counter", "cycle", "data", "dbtoa", "dcblock", "degrees", "degtorad",
    "delay", "delta", "dim", "div", "elapsed", "eq", "eqp", "exp", "exp2",
    "expr", "fastcos", "fastexp", "fastpow", "fastsin", "fasttan",
    "fftfullspect", "ffthop", "fftinfo", "fftoffset", "fftsize", "fixdenorm",
    "fixnan", "float", "floor", "fold", "fract", "ftom", "gate", "gen", "gt",
    "gte", "gtep", "gtp", "halfpi", "history", "hypot", "in", "int", "interp",
    "invpi", "isdenorm", "isnan", "latch", "ln", "ln10", "ln2", "log", "log10",
    "log10e", "log2", "log2e", "lookup", "lt", "lte", "ltep", "ltp", "max",
    "maximum", "mc_channel", "mc_channelcount", "min", "minimum", "mix", "mod",
    "mstosamps", "mtof", "mul", "mulequals", "nearest", "neg", "neq", "neqp",
    "noise", "not", "or", "out", "param", "pass", "peek", "phasewrap",
    "phasor", "phi", "pi", "plusequals", "poke", "poltocar", "pow", "radians",
    "radtodeg", "rate", "rdiv", "read", "receive", "rmod", "round", "rsub",
    "sah", "sample", "samplerate", "sampstoms", "scale", "selector", "send",
    "setparam", "sign", "sin", "sinh", "slide", "smoothstep", "splat", "sqrt",
    "sqrt1_2", "sqrt2", "step", "sub", "switch", "t60", "t60time", "tan",
    "tanh", "train", "triangle", "trunc", "twopi", "vectorsize", "voice",
    "voicecount", "wave", "wrap", "write", "xor",
})
assert len(GEN_OPERATOR_NAMES) == 162

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
_OUT_LIKE = re.compile(r"([A-Za-z]+)(\d+)$")


def _names_read(expr):
    """Yield every Name node an expression reads. Call names and Method
    objects are plain strings, never Name nodes, so they are not yielded."""
    if isinstance(expr, Name):
        yield expr
    elif isinstance(expr, Unary):
        yield from _names_read(expr.a)
    elif isinstance(expr, Bin):
        yield from _names_read(expr.a)
        yield from _names_read(expr.b)
    elif isinstance(expr, Tern):
        yield from _names_read(expr.c)
        yield from _names_read(expr.a)
        yield from _names_read(expr.b)
    elif isinstance(expr, (Call, Method)):
        for a in expr.args:
            yield from _names_read(a)


def _check_definite_assignment(stmts, defined: set, local_names: set, code: str,
                               ignored: frozenset = frozenset()) -> None:
    """CR-01: raise Unsupported when a local is read before it is assigned on
    every path (gen~ 'not defined').

    ``defined`` is updated in place with the names definitely assigned by
    ``stmts``. Names first assigned inside an if/else or for block are local
    to that block (gen variables are local-to-scope), so they never flow back
    out: the branches are checked on copies and not merged, and a for loop's
    counter and body names do not leak past the loop. Only names in
    ``local_names`` are checked; inN, outN, History, Param, constants and
    buffer names never are."""

    def fail(name, off):
        raise Unsupported(
            f"local '{name}' is read before it is assigned on every path "
            "(gen~ 'not defined'); assign it before the first read, outside "
            "any if/else or for block that sets it",
            _line_of(code, off),
        )

    def check(expr, scope):
        for node in _names_read(expr):
            if node.name in local_names and node.name not in scope:
                fail(node.name, node.off)

    def assign(s, scope):
        check(s.expr, scope)
        if s.op != "=" and s.name in local_names and s.name not in scope:
            fail(s.name, s.off)        # a compound assignment reads its target
        if id(s) not in ignored:
            scope.add(s.name)

    for s in stmts:
        if isinstance(s, Assign):
            assign(s, defined)
        elif isinstance(s, ExprStmt):
            check(s.expr, defined)
        elif isinstance(s, If):
            check(s.cond, defined)
            _check_definite_assignment(s.then, set(defined), local_names, code, ignored)
            if s.els:
                _check_definite_assignment(s.els, set(defined), local_names, code, ignored)
        elif isinstance(s, For):
            inner = set(defined)
            assign(s.init, inner)
            check(s.cond, inner)
            _check_definite_assignment(s.body, inner, local_names, code, ignored)
            assign(s.step, inner)


# WR-02: the subset of _STATEFUL_CALLS whose call site keeps state or writes.
# peek, dim, channels, selector and mc_* are pure reads. Any ``<obj>.write()``
# Method is flagged too.
_BRANCH_STATEFUL_CALLS = frozenset({"noise", "phasor", "cycle", "latch", "dcblock", "poke"})


def _branch_state_advisory(body, code: str) -> list:
    """WR-02: an INFO advisory naming every stateful call or write that sits
    inside an if/else body. Returns ``[]`` or one ``("branch_state", detail)``.

    The simulator runs only the taken branch, so such a call advances or
    writes only when its branch runs. A top-level if condition runs every
    sample and is not flagged; neither are ``?:`` operands (all evaluated)
    nor History assignments (both readings of the gen rule land the
    assignment only when the condition holds). Sites aggregate per construct
    in first-occurrence order, because a codebox can hold hundreds of pokes."""
    sites: dict = {}    # construct -> [count, first line], insertion-ordered

    def scan(expr):
        if isinstance(expr, Unary):
            scan(expr.a)
        elif isinstance(expr, Bin):
            scan(expr.a)
            scan(expr.b)
        elif isinstance(expr, Tern):
            scan(expr.c)
            scan(expr.a)
            scan(expr.b)
        elif isinstance(expr, (Call, Method)):
            if isinstance(expr, Call) and expr.name in _BRANCH_STATEFUL_CALLS:
                construct = f"{expr.name}()"
            elif isinstance(expr, Method) and expr.method == "write":
                construct = f"{expr.obj}.write()"
            else:
                construct = None
            if construct is not None:
                entry = sites.setdefault(construct, [0, _line_of(code, expr.off)])
                entry[0] += 1
            for a in expr.args:
                scan(a)

    def walk(stmts, inside: bool):
        for st in stmts:
            if isinstance(st, If):
                if inside:
                    scan(st.cond)
                walk(st.then, True)
                if st.els:
                    walk(st.els, True)
            elif isinstance(st, For):
                if inside:
                    scan(st.init.expr)
                    scan(st.cond)
                    scan(st.step.expr)
                walk(st.body, inside)
            elif isinstance(st, (Assign, ExprStmt)) and inside:
                scan(st.expr)

    walk(body, False)
    if not sites:
        return []
    entries = ", ".join(
        f"{c} (line {line})" if k == 1 else f"{c} x{k} (first at line {line})"
        for c, (k, line) in sites.items()
    )
    return [(
        "branch_state",
        f"{entries} inside an if/else branch: the simulator runs only the taken "
        "branch, so a stateful call there advances or writes only when its branch "
        "runs (simulator's choice, unconfirmed in MAX; genexpr-rules.md says both "
        "branches execute)",
    )]


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance (stdlib only; the names are short)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb_ in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb_)))
        prev = cur
    return prev[-1]


# ===========================================================================
# Value dataflow (261022-ud6 CR-01: smoke port inference)
# ===========================================================================

# Operators whose result is a 0/1 flag, not the operands' value.
_FLAG_OPS = frozenset({"<", ">", "<=", ">=", "==", "!=", "&&", "||"})
# Calls whose result does not carry an argument's value: generators read a
# rate (phasor, cycle, triangle phase), noise reads nothing, conversions of
# a time / a size are not audio.
_NO_VALUE_CALLS = frozenset({
    "phasor", "cycle", "noise", "triangle", "dim", "channels", "mstosamps",
    "sampstoms", "poke",
})


def value_dependencies(cb: "Codebox") -> dict:
    """{outN: {inK, ...}} -- which inlets reach each outlet as a value.

    A taint pass over every assignment (if/else and for bodies included,
    iterated to a fixed point so History feedback converges). A value flows
    through arithmetic and pure functions, the ``?:`` branches, ``latch``'s
    input, ``selector``'s inputs, ``dcblock``, and through a Buffer / Data /
    Delay that ``poke`` / ``.write()`` filled and ``peek`` / ``.read()``
    reads. It does not flow through index, channel, rate or time arguments,
    comparisons and logic (0/1 flags), ``?:`` / if conditions, or
    generators (phasor, cycle, noise, triangle). The smoke port inference
    uses it to decide whether a downstream gen~ inlet passes audio on.
    """
    taint: dict = {f"in{k}": {k} for k in range(1, cb.n_in + 1)}

    def srcs(e) -> set:
        if isinstance(e, Name):
            return taint.get(e.name, set())
        if isinstance(e, Unary):
            return srcs(e.a)
        if isinstance(e, Bin):
            return set() if e.op in _FLAG_OPS else srcs(e.a) | srcs(e.b)
        if isinstance(e, Tern):
            return srcs(e.a) | srcs(e.b)
        if isinstance(e, Method):
            return set(taint.get(e.obj, set())) if e.method == "read" else set()
        if isinstance(e, Call):
            if e.name == "peek":
                a0 = e.args[0] if e.args else None
                return set(taint.get(a0.name, set())) if isinstance(a0, Name) else set()
            if e.name in _NO_VALUE_CALLS:
                return set()
            if e.name == "latch":
                return srcs(e.args[0]) if e.args else set()
            if e.name == "selector":
                out: set = set()
                for a in e.args[1:]:
                    out |= srcs(a)
                return out
            out = set()
            for a in e.args:
                out |= srcs(a)
            return out
        return set()

    def side_effects(e) -> bool:
        changed = False
        for x in _subexprs(e):
            target, val = None, None
            if isinstance(x, Call) and x.name == "poke" and len(x.args) >= 2 \
                    and isinstance(x.args[0], Name):
                target, val = x.args[0].name, x.args[1]
            elif isinstance(x, Method) and x.method == "write" and x.args:
                target, val = x.obj, x.args[0]
            if target is not None:
                add = srcs(val) - taint.get(target, set())
                if add:
                    taint.setdefault(target, set()).update(add)
                    changed = True
        return changed

    stmts = list(_walk_stmts(cb.body))
    for _ in range(64):     # fixed point; bounded (each pass only grows sets)
        changed = False
        for s in stmts:
            if isinstance(s, (Assign, ExprStmt)):
                changed |= side_effects(s.expr)
            if isinstance(s, Assign):
                add = srcs(s.expr)
                if s.op != "=":
                    add = add | taint.get(s.name, set())
                add = add - taint.get(s.name, set())
                if add:
                    taint.setdefault(s.name, set()).update(add)
                    changed = True
        if not changed:
            break
    return {k: set(taint.get(f"out{k}", set())) for k in range(1, cb.n_out + 1)}


# ===========================================================================
# Build-time lint helpers (261022-ud6 IN-01, IN-02)
# ===========================================================================

# Names gen~ treats as fixed for a compile: they make an expression Param-only
# (hoistable) and make a loop bound runtime-variable.
_COMPILE_CONSTANT_NAMES = frozenset({"samplerate", "vectorsize"})


def _children(expr):
    if isinstance(expr, Unary):
        return (expr.a,)
    if isinstance(expr, Bin):
        return (expr.a, expr.b)
    if isinstance(expr, Tern):
        return (expr.c, expr.a, expr.b)
    if isinstance(expr, (Call, Method)):
        return tuple(expr.args)
    return ()


def _subexprs(expr):
    """Yield ``expr`` and every expression nested in it."""
    yield expr
    for c in _children(expr):
        yield from _subexprs(c)


def _stmt_expr_pairs(body):
    """(statement, expression) for every statement-level expression, recursing
    into if/else and for bodies (for init / step included)."""
    for s in _walk_stmts(body):
        for e in _stmt_exprs(s):
            yield s, e


def _all_names_read(body) -> set:
    """Every name any expression reads, plus compound-assignment targets."""
    names: set = set()
    for s, e in _stmt_expr_pairs(body):
        names.update(n.name for n in _names_read(e))
        if isinstance(s, Assign) and s.op != "=":
            names.add(s.name)
    return names


def _loop_bound_lint(body, param_names: frozenset, code: str) -> list:
    """IN-01 ``loop_bound_param``: a for bound that reads a Param, samplerate
    or vectorsize. The simulator folds those per corner, but gen~ compiles a
    Param as a runtime value, and genexpr-rules.md says CONSTANT bounds only
    (the two codeboxes that used variable bounds failed to compile)."""
    out: list = []
    variable = param_names | _COMPILE_CONSTANT_NAMES
    for s in _walk_stmts(body):
        if not isinstance(s, For) or not isinstance(s.cond, Bin):
            continue
        counter = s.init.name
        sides = [x for x in (s.cond.a, s.cond.b)
                 if not (isinstance(x, Name) and x.name == counter)]
        names = sorted({n.name for x in sides for n in _names_read(x)} & variable)
        if names:
            out.append((
                "loop_bound_param",
                f"line {_line_of(code, s.off)}: for loop bound reads "
                + ", ".join(f"'{n}'" for n in names)
                + "; the codebox safe-construct rules say CONSTANT bounds "
                "(for (i = 0; i < 600; i += 1)) with a variable inner guard "
                "(if (i < n) { ... }) (genexpr-rules.md)",
            ))
    return out


def _param_only(expr, allowed: set) -> bool:
    """True when ``expr`` reads only ``allowed`` names and calls only pure
    built-ins: gen~ would treat it as Param-only and hoist it."""
    if isinstance(expr, Num):
        return True
    if isinstance(expr, Name):
        return expr.name in allowed
    if isinstance(expr, Str) or isinstance(expr, Method):
        return False
    if isinstance(expr, Call) and expr.name not in _PURE:
        return False
    return all(_param_only(c, allowed) for c in _children(expr))


def _hoist_alias_lint(body, param_names: frozenset, local_names: set, code: str) -> list:
    """IN-01 ``hoist_alias``: a statement whose whole right-hand side (or if
    condition) is Param-only and reads a local alias.

    genexpr-rules.md "No local aliases in Param-only expressions": gen~ hoists
    Param-only expressions out of the per-sample body, and a loop-local alias
    such as ``sr = samplerate;`` or ``RING = 1344000;`` is not visible there
    ("use of undeclared identifier"). An alias is a top-level local whose every
    assignment is a bare samplerate / vectorsize / Param / constant name or a
    number literal. Computed setup locals (``tanh_drive = tanh(drive);``) and
    Param-only sub-expressions inside a per-sample statement are not flagged:
    user-confirmed codeboxes use both and compile."""
    top: dict = {}
    nested: set = set()

    def collect(stmts, at_top):
        for s in stmts:
            if isinstance(s, Assign):
                if at_top:
                    top.setdefault(s.name, []).append(s)
                else:
                    nested.add(s.name)
            elif isinstance(s, If):
                collect(s.then, False)
                collect(s.els or (), False)
            elif isinstance(s, For):
                nested.update((s.init.name, s.step.name))
                collect(s.body, False)

    collect(body, True)
    base = set(param_names) | set(GEN_CONSTANTS) | _COMPILE_CONSTANT_NAMES

    def is_alias_rhs(a):
        e = a.expr
        return a.op == "=" and (isinstance(e, Num) or (isinstance(e, Name) and e.name in base))

    aliases = {
        n for n, assigns in top.items()
        if n in local_names and n not in nested and all(is_alias_rhs(a) for a in assigns)
    }
    if not aliases:
        return []
    allowed = base | aliases
    sites: list = []    # (line, sorted alias names)
    for s, e in _stmt_expr_pairs(body):
        if isinstance(s, Assign) and s.name in aliases:
            continue
        if isinstance(e, (Num, Name, Str)) or not _param_only(e, allowed):
            continue
        used = sorted({n.name for n in _names_read(e)} & aliases)
        if used:
            sites.append((_line_of(code, s.off), used))
    if not sites:
        return []
    line, used = sites[0]
    more = f" ({len(sites)} sites)" if len(sites) > 1 else ""
    return [(
        "hoist_alias",
        f"line {line}: Param-only expression reads the local "
        + ", ".join(f"'{n}'" for n in used)
        + f"{more}, a bare alias of samplerate / a Param / a constant; "
        "gen~ hoists such expressions out of the per-sample loop, where the alias "
        "can be undeclared ('use of undeclared identifier'). Write samplerate and "
        "the Param expression directly, or de-hoist with History one(1) "
        "(genexpr-rules.md)",
    )]


def _implicit_channel_lint(body, decls, code: str) -> list:
    """IN-01 ``implicit_channel``: peek(buf, i) / poke(buf, v, i) without the
    explicit channel argument the codebox safe-construct rules require."""
    sites: dict = {}    # construct -> [count, first line]
    for s, e in _stmt_expr_pairs(body):
        for x in _subexprs(e):
            if isinstance(x, Call) and (
                (x.name == "peek" and len(x.args) == 2)
                or (x.name == "poke" and len(x.args) == 3)
            ):
                entry = sites.setdefault(f"{x.name}()", [0, _line_of(code, x.off)])
                entry[0] += 1
    if not sites:
        return []
    ordered = sorted(sites.items(), key=lambda kv: kv[1][1])
    entries = ", ".join(
        f"{c} (line {line})" if k == 1 else f"{c} x{k} (first at line {line})"
        for c, (k, line) in ordered
    )
    return [(
        "implicit_channel",
        f"{entries} without an explicit channel argument; the codebox "
        "safe-construct rules say peek(buf, idx, 0) / poke(buf, val, idx, 0) "
        "(genexpr-rules.md)",
    )]


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
    lint: list = field(default_factory=list)   # [(check, detail)] build-time WARNs
    advisories: list = field(default_factory=list)  # [(check, detail)] build-time INFOs

    def build(
        self,
        *,
        params: dict | None = None,
        samplerate: float = 44100.0,
        seed: int = 1,
        buffers: dict | None = None,
        buffer_scale: float = 1.0,
    ) -> "Program":
        """Compile this codebox for one Param corner.

        ``params`` overrides Param values by name (a name that is not a
        declared Param raises ValueError). ``buffer_scale`` multiplies the
        offline Buffer backing (the smoke self-sustain rerun scales it with
        the stimulus, 261022-ud6). Raises Unsupported for anything the
        interpreter cannot run.
        """
        return _Builder(
            self, params or {}, float(samplerate), seed, buffers or {}, float(buffer_scale)
        ).program()


def _clamp_param(value, p: dict) -> float:
    """WR-04: clamp a Param value to its declared [min, max] the RNBO
    genexpr_js way (below min -> min, then above max -> max)."""
    v = float(value)
    if p.get("min") is not None and v < p["min"]:
        v = float(p["min"])
    if p.get("max") is not None and v > p["max"]:
        v = float(p["max"])
    return v


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
        p["default"] = _clamp_param(p["default"], p)
        params.append(p)

    # Assignment targets.
    warnings: list = []
    locals_: list = []
    ignored: set = set()
    first_off: dict = {}
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
        if name not in first_off:
            first_off[name] = s.off
            locals_.append(name)

    # CR-01: every local read must follow an assignment on every path.
    _check_definite_assignment(body, set(), set(locals_), code, frozenset(ignored))

    # Build-time lint (WARN findings in smoke).
    lint: list = []
    tab_at = code.find("\t")
    if tab_at >= 0:
        lint.append((
            "tab_char",
            f"line {_line_of(code, tab_at)}: tab character in the codebox; "
            "the codebox safe-construct rules say spaces only (genexpr-rules.md)",
        ))
    # IN-02 (261022-ud6): only a local that is never read can be a typo for
    # an output; a read local (cut1, oct2) reaches an outlet through its reader.
    read_names = _all_names_read(body)
    for name in locals_:
        m = _OUT_LIKE.match(name)
        if (m and not _OUT_NAME.match(name) and name not in read_names
                and _edit_distance(m.group(1).lower(), "out") <= 1):
            lint.append((
                "output_typo",
                f"line {_line_of(code, first_off[name])}: local '{name}' looks like a "
                "misspelled output (outputs are out1..outN) and is never read, so it "
                "never reaches an outlet",
            ))
    # IN-01 (261022-ud6): the genexpr-rules.md codebox safe-construct rules.
    param_names = frozenset(p["name"] for p in params)
    lint.extend(_loop_bound_lint(body, param_names, code))
    lint.extend(_hoist_alias_lint(body, param_names, set(locals_), code))
    lint.extend(_implicit_channel_lint(body, decls, code))

    # Build-time advisories (INFO findings in smoke; never move a verdict).
    advisories: list = _branch_state_advisory(body, code)

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
        lint=lint,
        advisories=advisories,
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
    # 261022-ud6 WR-04: math.exp2 is Python 3.11+; the declared target is 3.10.
    try:
        return 2.0 ** x
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


def _triangle(phase, duty=0.5):
    p = _wrap(phase)
    if p != p:
        return _NAN
    d = min(max(duty, 0.0), 1.0)
    if p < d:
        return p / d
    return (1.0 - p) / (1.0 - d) if d < 1.0 else 0.0


def _selector(i, *vals):
    if not (i >= 1.0):          # nan and values <= 0 give 0.0
        return 0.0
    k = len(vals) if i >= len(vals) else int(i)
    return vals[k - 1]


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
    "triangle": (_triangle, (1, 2)),
    # mstosamps / sampstoms are bound to the build samplerate in _Builder.
    "mstosamps": (None, (1,)),
    "sampstoms": (None, (1,)),
}

_MC_NAMES = ("mc_channel", "mc_channelcount")   # simulated as one channel
_BUFFER_FRAMES = 48000                            # default Buffer backing
_BUFFER_CHANS = 1
_BUFFER_HZ = 220.0
_BUFFER_AMP = 0.25


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
    def __init__(self, cb: Codebox, params: dict, samplerate: float, seed, buffers: dict,
                 buffer_scale: float = 1.0):
        self.cb = cb
        self.code = cb.code
        self.samplerate = samplerate
        self.seed = seed
        self.buffers = buffers
        self.buffer_scale = buffer_scale
        pvals = {p["name"]: float(p["default"]) for p in cb.params}
        by_name = {p["name"]: p for p in cb.params}
        for k, v in params.items():
            if k not in pvals:
                raise ValueError(f"not a declared Param: {k!r}")
            pvals[k] = _clamp_param(v, by_name[k])
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
        self.post: list = []   # end-of-sample callbacks (Delay heads)
        self.delays: dict = {}  # name -> (ring, head cell, N, L)
        self.bufs: dict = {}    # name -> (channel lists, frames, chans)
        self.state_total = 0
        self.rng = random.Random(seed)

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
            if d.kwargs:
                raise self.err(f"keyword arguments in the {d.dtype} '{d.name}'", d.off)
            if d.dtype == "Delay":
                self._delay_decl(d)
            elif d.dtype == "Data":
                self._data_decl(d)
            else:
                self._buffer_decl(d)

    def _const_int(self, node, what, d) -> int:
        ce = self.expr(node)
        if ce[0] != _C or not math.isfinite(ce[1]):
            raise self.err(f"non-constant {what} for {d.dtype} '{d.name}'", d.off)
        v = int(math.ceil(ce[1]))
        if v < 1:
            raise self.err(f"{what} of {d.dtype} '{d.name}' must be >= 1", d.off)
        return v

    def _reserve(self, count: int, d) -> None:
        self.state_total += count
        if self.state_total > STATE_CAP:
            raise self.err(
                f"state cap exceeded: {self.state_total} Delay/Data/Buffer samples "
                f"> STATE_CAP {STATE_CAP}",
                d.off,
            )

    def _delay_decl(self, d) -> None:
        if not d.args or len(d.args) > 2:
            raise self.err(f"Delay '{d.name}' needs one size argument", d.off)
        size = self._const_int(d.args[0], "size", d)
        if len(d.args) == 2:
            ce = self.expr(d.args[1])
            if ce != (_C, 1.0):
                raise self.err(f"multi-tap Delay '{d.name}' (second argument)", d.off)
        length = size + 2
        self._reserve(length, d)
        ring = [0.0] * length
        head = [0]

        def advance():
            h = head[0] + 1
            if h == length:
                h = 0
            head[0] = h
            ring[h] = 0.0       # an unwritten sample reads as 0
        self.post.append(advance)
        self.delays[d.name] = (ring, head, size, length)

    def _data_decl(self, d) -> None:
        if not d.args or len(d.args) > 2:
            raise self.err(f"Data '{d.name}' needs a frame count", d.off)
        frames = self._const_int(d.args[0], "frame count", d)
        chans = self._const_int(d.args[1], "channel count", d) if len(d.args) == 2 else 1
        self._reserve(frames * chans, d)
        self.bufs[d.name] = ([[0.0] * frames for _ in range(chans)], frames, chans)

    def _buffer_decl(self, d) -> None:
        if len(d.args) > 1 or (d.args and not isinstance(d.args[0], Str)):
            raise self.err(
                f"Buffer '{d.name}' takes one string argument (the buffer~ name)", d.off
            )
        bufname = d.args[0].value if d.args else d.name
        spec = self.buffers.get(bufname, (_BUFFER_FRAMES, _BUFFER_CHANS))
        try:
            frames, chans = int(spec[0]), int(spec[1])
        except (TypeError, ValueError, IndexError):
            raise ValueError(f"buffers[{bufname!r}] must be (frames, channels)") from None
        if frames < 1 or chans < 1:
            raise ValueError(f"buffers[{bufname!r}] needs frames >= 1 and channels >= 1")
        self._reserve(frames * chans, d)
        n = np.arange(frames, dtype=float)
        amp = _BUFFER_AMP * self.buffer_scale
        wave = (amp * np.sin(2.0 * np.pi * _BUFFER_HZ * n / self.samplerate)).tolist()
        self.bufs[d.name] = ([list(wave) for _ in range(chans)], frames, chans)

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
        if n in _MC_NAMES:
            return (_C, 1.0)
        if n in GEN_OPERATOR_NAMES and not _IN_NAME.match(n):
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
        handler = _STATEFUL_CALLS.get(name)
        if handler is not None:
            return handler(self, node)
        if name in GEN_OPERATOR_NAMES:
            raise self.err(f"Gen operator not implemented: {name}", node.off)
        raise self.err(f"unknown function: {name}", node.off)

    def arity(self, node, *allowed) -> None:
        if len(node.args) not in allowed:
            want = " or ".join(str(a) for a in allowed)
            raise self.err(
                f"{node.name}() takes {want} argument(s), got {len(node.args)}", node.off
            )

    def buf_arg(self, node, arg):
        if not isinstance(arg, Name) or arg.name not in self.bufs:
            raise self.err(
                f"{node.name}() needs a Data or Buffer name as its first argument",
                node.off,
            )
        return self.bufs[arg.name]

    def method(self, node: Method):
        if node.obj not in self.delays:
            d = self.declared.get(node.obj)
            what = f"{d.dtype} '{node.obj}'" if d else f"'{node.obj}'"
            raise self.err(f"method call {what}.{node.method}()", node.off)
        ring, head, size, length = self.delays[node.obj]
        nargs = len(node.args)
        if node.method == "read":
            if nargs != 1:
                raise self.err(
                    f"Delay read() takes 1 argument, got {nargs}", node.off
                )
            t = self.expr(node.args[0])
            if t[0] == _C:
                tv = t[1]
                if tv != tv:
                    return (_C, _NAN)
                tv = min(max(tv, 1.0), float(size))
                i = int(tv)
                f = tv - i
                if f == 0.0:
                    return (_F, lambda env: ring[(head[0] - i) % length])
                g = 1.0 - f
                return (_F, lambda env: g * ring[(head[0] - i) % length]
                        + f * ring[(head[0] - i - 1) % length])
            ft = _as_fn(t)
            top = float(size)

            def read(env):
                tv = ft(env)
                if tv != tv:
                    return _NAN
                if tv < 1.0:
                    tv = 1.0
                elif tv > top:
                    tv = top
                i = int(tv)
                f = tv - i
                h = head[0]
                a = ring[(h - i) % length]
                if f == 0.0:
                    return a
                return (1.0 - f) * a + f * ring[(h - i - 1) % length]
            return (_F, read)
        if node.method == "write":
            if nargs != 1:
                raise self.err(
                    f"Delay write() takes 1 argument, got {nargs}", node.off
                )
            fx = _as_fn(self.expr(node.args[0]))

            def write(env):
                ring[head[0]] = fx(env)
                return 0.0
            return (_F, write)
        raise self.err(f"Delay method '{node.obj}.{node.method}()'", node.off)

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
            return [self.for_loop(s)]
        raise self.err(f"statement {type(s).__name__}", getattr(s, "off", 0))

    def for_loop(self, s: For):
        counter = s.init.name
        if s.init.op != "=" or counter not in self.cb._locals:
            raise self.err(
                "for loop init must assign a local counter ('i = 0')", s.off
            )
        cond = s.cond
        if not (isinstance(cond, Bin) and cond.op in ("<", "<=", ">", ">=", "!=", "==")):
            raise self.err("for loop condition must compare the counter", s.off)
        if isinstance(cond.a, Name) and cond.a.name == counter:
            bound = cond.b
        elif isinstance(cond.b, Name) and cond.b.name == counter:
            bound = cond.a
        else:
            raise self.err(
                f"for loop condition must compare the counter '{counter}'", s.off
            )
        if self.expr(bound)[0] != _C:
            raise self.err("for loop bound is not constant", s.off)
        if s.step.name != counter:
            raise self.err(
                f"for loop step must update the counter '{counter}'", s.off
            )
        (finit,) = self.stmt(s.init)
        (fstep,) = self.stmt(s.step)
        fcond = _as_fn(self.expr(cond))
        body = tuple(self.stmts(s.body))
        line = _line_of(self.code, s.off)
        cap = LOOP_CAP

        def loop(env):
            finit(env)
            k = 0
            while fcond(env) != 0.0:
                k += 1
                if k > cap:
                    raise Unsupported(
                        f"for loop exceeded {cap} iterations in one sample", line
                    )
                for st in body:
                    st(env)
                fstep(env)
        return loop

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
# Stateful and buffer built-ins (one state cell per call site)
# ===========================================================================


def _call_peek(b: _Builder, node: Call):
    b.arity(node, 2, 3)
    chs, frames, nch = b.buf_arg(node, node.args[0])
    fi = _as_fn(b.expr(node.args[1]))
    top = float(frames)
    if len(node.args) == 2:
        c = (_C, 0.0)
    else:
        c = b.expr(node.args[2])
    if c[0] == _C:
        cv = c[1]
        if not (0.0 <= cv < nch):
            def peek_off(env):
                fi(env)
                return 0.0
            return (_F, peek_off)
        ch = chs[int(cv)]

        def peek(env):
            x = fi(env)
            return ch[int(x)] if 0.0 <= x < top else 0.0
        return (_F, peek)
    fc = _as_fn(c)

    def peek_ch(env):
        x = fi(env)
        cv = fc(env)
        if 0.0 <= x < top and 0.0 <= cv < nch:
            return chs[int(cv)][int(x)]
        return 0.0
    return (_F, peek_ch)


def _call_poke(b: _Builder, node: Call):
    b.arity(node, 3, 4)
    chs, frames, nch = b.buf_arg(node, node.args[0])
    fv = _as_fn(b.expr(node.args[1]))
    fi = _as_fn(b.expr(node.args[2]))
    fc = _as_fn(b.expr(node.args[3])) if len(node.args) == 4 else (lambda env: 0.0)
    top = float(frames)

    def poke(env):
        v = fv(env)
        x = fi(env)
        cv = fc(env)
        if 0.0 <= x < top and 0.0 <= cv < nch:
            chs[int(cv)][int(x)] = v
        return 0.0
    return (_F, poke)


def _call_dim(b: _Builder, node: Call):
    b.arity(node, 1)
    _chs, frames, _nch = b.buf_arg(node, node.args[0])
    return (_C, float(frames))


def _call_channels(b: _Builder, node: Call):
    b.arity(node, 1)
    _chs, _frames, nch = b.buf_arg(node, node.args[0])
    return (_C, float(nch))


def _call_noise(b: _Builder, node: Call):
    b.arity(node, 0)
    r = b.rng.random
    # Same stream as genrun's random.uniform(-1, 1) after random.seed(seed).
    return (_F, lambda env: -1 + 2 * r())


def _advance_phase(p: float, inc: float) -> float:
    q = p + inc
    if q >= 1.0 or q < 0.0:
        try:
            q -= math.floor(q)
        except (ValueError, OverflowError):
            return _NAN
        if q >= 1.0:
            q = 0.0
    return q


def _call_phasor(b: _Builder, node: Call):
    b.arity(node, 1, 2)
    ff = _as_fn(b.expr(node.args[0]))
    fr = _as_fn(b.expr(node.args[1])) if len(node.args) == 2 else None
    sr = b.samplerate
    cell = [0.0]

    def phasor(env):
        f = ff(env)
        if fr is not None and fr(env) != 0.0:
            cell[0] = 0.0
        p = cell[0]
        cell[0] = _advance_phase(p, f / sr)
        return p
    return (_F, phasor)


def _call_cycle(b: _Builder, node: Call):
    b.arity(node, 1)
    ff = _as_fn(b.expr(node.args[0]))
    sr = b.samplerate
    cell = [0.0]
    twopi = 2 * math.pi

    def cycle(env):
        f = ff(env)
        p = cell[0]
        cell[0] = _advance_phase(p, f / sr)
        return _sin(twopi * p)
    return (_F, cycle)


def _call_latch(b: _Builder, node: Call):
    b.arity(node, 2)
    fx = _as_fn(b.expr(node.args[0]))
    fc = _as_fn(b.expr(node.args[1]))
    cell = [0.0]

    def latch(env):
        x = fx(env)
        if fc(env) != 0.0:
            cell[0] = x
        return cell[0]
    return (_F, latch)


def _call_dcblock(b: _Builder, node: Call):
    b.arity(node, 1)
    fx = _as_fn(b.expr(node.args[0]))
    st = [0.0, 0.0]   # x1, y1

    def dcblock(env):
        x = fx(env)
        y = x - st[0] + 0.9997 * st[1]
        st[0] = x
        st[1] = y
        return y
    return (_F, dcblock)


def _call_selector(b: _Builder, node: Call):
    if len(node.args) < 2:
        raise b.err(
            f"selector() takes at least 2 arguments, got {len(node.args)}", node.off
        )
    args = [b.expr(a) for a in node.args]
    if all(k == _C for k, _x in args):
        return (_C, _selector(*[x for _k, x in args]))
    fs = tuple(_as_fn(a) for a in args)
    return (_F, lambda env: _selector(*[f(env) for f in fs]))


def _call_mc(b: _Builder, node: Call):
    b.arity(node, 0)
    return (_C, 1.0)


_STATEFUL_CALLS = {
    "peek": _call_peek,
    "poke": _call_poke,
    "dim": _call_dim,
    "channels": _call_channels,
    "noise": _call_noise,
    "phasor": _call_phasor,
    "cycle": _call_cycle,
    "latch": _call_latch,
    "dcblock": _call_dcblock,
    "selector": _call_selector,
    "mc_channel": _call_mc,
    "mc_channelcount": _call_mc,
}
assert _BRANCH_STATEFUL_CALLS <= set(_STATEFUL_CALLS)


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
