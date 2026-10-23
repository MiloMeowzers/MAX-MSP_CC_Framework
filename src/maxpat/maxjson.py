"""MAX JSON layout writers (fix-plan Q29, review B9; 261022-ud6 WR-03).

MAX 9 saves patchers with short scalar arrays on one line
(``"rect": [ 34.0, 104.0, 1333.0, 617.0 ]``), while ``json.dumps(indent=...)``
puts one array element per line. Writing a MAX-saved file back with
json.dumps therefore rewrites the whole file and buries every real change.
Max 5 to 9.0.x write a third, legacy layout (tab indent, ``"key" : value``,
``}`` + newline before a separating comma).

Provides:
- dumps_max: Serialize a JSON value in MAX 9.1+'s own layout.
- dumps_legacy: Serialize in the legacy Max 5 - 9.0.x layout.
- dumps_expanded: Serialize in the ``json.dumps(indent=...)`` layout.
- detect_layout: Which of the three layouts a file text uses.
- has_expanded_arrays: True when a JSON text uses the json.dumps layout
  (a non-empty scalar array spread over several lines).
- RawSpellings: The file's own spelling of numbers and strings whose
  default ``json.dumps`` spelling differs (``11.595186999999999``,
  ``"\\u002c"``), so a rewrite keeps them.
- json_identical: Strict JSON equality (types, key order, list order).

This module is pure: it imports neither hooks nor patcher.

MAX 9.1+ layout rules (measured on 1015 of 1015 bundled Max 9.0-9.3 help
patches, byte for byte):

- non-empty dict: ``{``, one ``key: value`` line per item at the inner
  indent joined by ``,`` + newline, then a newline and ``}`` at the pad;
- empty dict: ``{`` + pad + ``}`` (MAX puts the closing pad inside);
- empty list: ``[]``;
- list whose elements are all scalars: ``[ a, b, c ]`` on one line;
- list holding any dict/list: expanded, one element per inner line;
- scalars and keys: ``json.dumps(..., ensure_ascii=False)``.

There is no trailing newline; ``hooks.format_patch_text`` adds one when the
original file had it.

Legacy layout rules (Max 5 - 9.0.x; measured on user and package files,
see dumps_legacy): a dict at depth d is ``tab*d + "{" + newline``,
its items at ``tab*(d+1)`` as ``"key" : value`` joined by ``,`` + newline,
then newline + ``tab*d + "}"`` + newline; a list is ``"[ "`` + elements
joined by ``", "`` + ``" ]"`` (empty: ``"[  ]"``), its elements one level
deeper. The text ends with ``}`` + newline. Line endings (CRLF on files
saved on Windows) are the caller's business.
"""

from __future__ import annotations

import json
import re
from collections import Counter

__all__ = [
    "dumps_max",
    "dumps_legacy",
    "dumps_expanded",
    "detect_layout",
    "has_expanded_arrays",
    "RawSpellings",
    "json_identical",
]

# A '[' followed by a newline and the start of a scalar: the json.dumps
# layout. A newline inside a JSON string is always escaped, so string
# payloads cannot match.
_EXPANDED_ARRAY_RE = re.compile(r'\[\r?\n[ \t]*(?:-?\d|"|true|false|null)')

# A tab-indented key followed by MAX's legacy " : " separator.
_LEGACY_KEY_RE = re.compile(r'\n\t+"(?:[^"\\\n]|\\.)*" : ')

# JSON tokens scanned left to right: strings (a number or brace inside a
# string is consumed by the string match), numbers, literals, structure.
_SCAN_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?'
    r'|true|false|null|[{}\[\]:,]'
)
_WS = " \t\r\n"


def _next_is_colon(text: str, pos: int) -> bool:
    """True when the next non-whitespace character at/after *pos* is ':'."""
    n = len(text)
    while pos < n and text[pos] in _WS:
        pos += 1
    return pos < n and text[pos] == ":"


def has_expanded_arrays(text: str) -> bool:
    """True when *text* holds a non-empty scalar array spread over lines.

    That is the ``json.dumps(indent=...)`` layout the framework used to
    write; MAX 9 writes scalar arrays inline.
    """
    return _EXPANDED_ARRAY_RE.search(text) is not None


def detect_layout(text: str) -> str:
    """``"legacy"``, ``"expanded"`` or ``"max9"`` for a JSON file text.

    legacy: tab-indented ``"key" : value`` (Max 5 - 9.0.x); expanded: the
    json.dumps layout; max9: everything else (MAX 9.1+, new files).
    """
    if _LEGACY_KEY_RE.search(text.replace("\r\n", "\n")) is not None:
        return "legacy"
    if has_expanded_arrays(text):
        return "expanded"
    return "max9"


def _scalar_key(value):
    """Hashable (type, value) key; bool and int stay apart."""
    return (type(value).__name__, value)


class RawSpellings:
    """The original text's spelling of scalars json.dumps would spell differently.

    Built from a file's text: every string and number token is decoded,
    and when ``json.dumps(decoded, ensure_ascii=False)`` differs from the
    token as written (``11.595186999999999``, ``"\\u003b"``), the written
    token is remembered per context -- the key of the innermost enclosing
    dict entry (list elements share their list's key), ``None`` for keys
    themselves -- and per value alone as the fallback; the most frequent
    spelling wins where a value is spelled several ways. ``spell(value,
    ctx)`` returns that spelling, else the json.dumps one, so values a
    patch edit introduced are spelled by json.dumps.
    """

    def __init__(self, text: str | None = None) -> None:
        self._ctx: dict = {}
        self._any: dict = {}
        if not text:
            return
        by_ctx: dict = {}
        by_any: dict = {}
        # Structure-aware scan: a stack of [kind, current key] frames.
        stack: list = []
        pending_key = None
        for m in _SCAN_RE.finditer(text):
            tok = m.group(0)
            c = tok[0]
            if c in "{[":
                ctx = stack[-1][1] if stack else None
                stack.append(["d" if c == "{" else "l", ctx])
                continue
            if c in "}]":
                if stack:
                    stack.pop()
                continue
            if c == ":":
                if stack and pending_key is not None:
                    stack[-1][1] = pending_key
                pending_key = None
                continue
            if c == ",":
                continue
            try:
                value = json.loads(tok)
            except ValueError:
                continue
            is_key = (
                c == '"' and stack and stack[-1][0] == "d"
                and _next_is_colon(text, m.end())
            )
            if is_key:
                pending_key = value
                ctx = None
            else:
                ctx = stack[-1][1] if stack else None
            if isinstance(value, (bool, type(None))) or (
                isinstance(value, float) and value != value
            ):
                continue
            sk = _scalar_key(value)
            by_ctx.setdefault((ctx, sk), Counter())[tok] += 1
            if json.dumps(value, ensure_ascii=False) != tok:
                by_any.setdefault(sk, Counter())[tok] += 1
        # Keep only values spelled non-default somewhere: per context the
        # winning spelling (default included), else the overall winner.
        self._any = {k: c.most_common(1)[0][0] for k, c in by_any.items()}
        self._ctx = {
            k: c.most_common(1)[0][0] for k, c in by_ctx.items() if k[1] in self._any
        }

    def __len__(self) -> int:
        return len(self._any)

    def spell(self, value, ctx=None) -> str:
        if self._any:
            try:
                sk = _scalar_key(value)
                raw = self._ctx.get((ctx, sk))
                if raw is None:
                    raw = self._any.get(sk)
            except TypeError:
                raw = None
            if raw is not None:
                return raw
        return json.dumps(value, ensure_ascii=False)


_DEFAULT_SPELL = RawSpellings()


def _key_str(key, spell) -> str:
    """Convert a dict key the way json.dumps does, then quote it."""
    if isinstance(key, str):
        k = key
    elif key is True:
        k = "true"
    elif key is False:
        k = "false"
    elif key is None:
        k = "null"
    elif isinstance(key, (int, float)):
        k = json.dumps(key)
    else:
        raise TypeError(
            f"keys must be str, int, float, bool or None, not {type(key).__name__}"
        )
    return spell.spell(k)


def _is_container(value) -> bool:
    return isinstance(value, (dict, list, tuple))


def _dump(value, indent: str, level: int, out: list, spell, ctx=None) -> None:
    if isinstance(value, dict):
        pad = indent * level
        if not value:
            out.append("{" + pad + "}")
            return
        inner = indent * (level + 1)
        out.append("{\n")
        first = True
        for k, v in value.items():
            if not first:
                out.append(",\n")
            first = False
            out.append(inner + _key_str(k, spell) + ": ")
            _dump(v, indent, level + 1, out, spell, k)
        out.append("\n" + pad + "}")
        return
    if isinstance(value, (list, tuple)):
        if not value:
            out.append("[]")
            return
        if not any(_is_container(e) for e in value):
            out.append("[ " + ", ".join(spell.spell(e, ctx) for e in value) + " ]")
            return
        pad = indent * level
        inner = indent * (level + 1)
        out.append("[\n")
        first = True
        for e in value:
            if not first:
                out.append(",\n")
            first = False
            out.append(inner)
            _dump(e, indent, level + 1, out, spell, ctx)
        out.append("\n" + pad + "]")
        return
    out.append(spell.spell(value, ctx))


def dumps_max(obj, indent: str = "    ", spellings: RawSpellings | None = None) -> str:
    """Serialize *obj* in MAX 9's JSON layout (no trailing newline).

    Key order is kept, never sorted. ``json.loads(dumps_max(x)) == x``.

    Args:
        obj: A JSON-serializable value (normally a patcher dict).
        indent: One indentation step (MAX writes 4 spaces).
        spellings: Optional RawSpellings of the file being rewritten.

    Returns:
        The JSON text.
    """
    out: list[str] = []
    _dump(obj, indent, 0, out, spellings or _DEFAULT_SPELL)
    return "".join(out)


def _dump_legacy(value, level: int, out: list, spell, ctx=None) -> None:
    if isinstance(value, dict):
        pad = "\t" * level
        inner = "\t" * (level + 1)
        out.append(pad + "{\n")
        first = True
        for k, v in value.items():
            if not first:
                out.append(",\n")
            first = False
            out.append(inner + _key_str(k, spell) + " : ")
            _dump_legacy(v, level + 1, out, spell, k)
        out.append("\n" + pad + "}\n")
        return
    if isinstance(value, (list, tuple)):
        out.append("[ ")
        first = True
        for e in value:
            if not first:
                out.append(", ")
            first = False
            _dump_legacy(e, level + 1, out, spell, ctx)
        out.append(" ]")
        return
    out.append(spell.spell(value, ctx))


def dumps_legacy(obj, spellings: RawSpellings | None = None) -> str:
    """Serialize *obj* in the legacy Max 5 - 9.0.x layout (review 261022-ud6 WR-03).

    The text ends with a newline (``}`` + newline, as MAX writes it) and
    uses ``\\n`` line endings. With the file's RawSpellings it reproduces,
    byte for byte (CRLF normalised), 262 of 262 MAX-saved tab-layout files
    in the user's projects (Max 5.1 - 9.0.7) and 2892 of 3279 package files;
    the rest are script-written package help files (stray blank lines,
    space indents) that a no-op save still leaves untouched
    (``hooks.format_patch_text`` returns the original text).
    """
    out: list[str] = []
    _dump_legacy(obj, 0, out, spellings or _DEFAULT_SPELL)
    return "".join(out)


def _dump_expanded(value, indent: str, level: int, out: list, spell, ctx=None) -> None:
    if isinstance(value, dict):
        if not value:
            out.append("{}")
            return
        pad = indent * level
        inner = indent * (level + 1)
        out.append("{\n")
        first = True
        for k, v in value.items():
            if not first:
                out.append(",\n")
            first = False
            out.append(inner + _key_str(k, spell) + ": ")
            _dump_expanded(v, indent, level + 1, out, spell, k)
        out.append("\n" + pad + "}")
        return
    if isinstance(value, (list, tuple)):
        if not value:
            out.append("[]")
            return
        pad = indent * level
        inner = indent * (level + 1)
        out.append("[\n")
        first = True
        for e in value:
            if not first:
                out.append(",\n")
            first = False
            out.append(inner)
            _dump_expanded(e, indent, level + 1, out, spell, ctx)
        out.append("\n" + pad + "]")
        return
    out.append(spell.spell(value, ctx))


def dumps_expanded(obj, indent: str = "    ", spellings: RawSpellings | None = None) -> str:
    """Serialize *obj* like ``json.dumps(obj, indent=indent, ensure_ascii=False)``.

    Identical to json.dumps without *spellings*; with them, scalars keep the
    rewritten file's own spelling.
    """
    out: list[str] = []
    _dump_expanded(obj, indent, 0, out, spellings or _DEFAULT_SPELL)
    return "".join(out)


def json_identical(a, b) -> bool:
    """Strict JSON equality: same types (bool, int and float apart), same
    dict key order, same list order. ``==`` would call ``1``, ``1.0`` and
    ``True`` equal and ignore key order."""
    if type(a) is not type(b):
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            pass
        else:
            return False
    if isinstance(a, dict):
        if list(a.keys()) != list(b.keys()):
            return False
        return all(json_identical(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(json_identical(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and a != a:
        return b != b
    return a == b
