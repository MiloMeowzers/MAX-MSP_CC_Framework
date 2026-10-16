"""MAX 9 JSON layout writer (fix-plan Q29, review B9).

MAX 9 saves patchers with short scalar arrays on one line
(``"rect": [ 34.0, 104.0, 1333.0, 617.0 ]``), while ``json.dumps(indent=...)``
puts one array element per line. Writing a MAX-saved file back with
json.dumps therefore rewrites the whole file and buries every real change.

Provides:
- dumps_max: Serialize a JSON value in MAX 9's own layout.
- has_expanded_arrays: True when a JSON text uses the json.dumps layout
  (a non-empty scalar array spread over several lines).

This module is pure: it imports neither hooks nor patcher. Layout rules
(measured on 1015 of 1015 bundled Max 9.0-9.3 help patches, byte for byte):

- non-empty dict: ``{``, one ``key: value`` line per item at the inner
  indent joined by ``,`` + newline, then a newline and ``}`` at the pad;
- empty dict: ``{`` + pad + ``}`` (MAX puts the closing pad inside);
- empty list: ``[]``;
- list whose elements are all scalars: ``[ a, b, c ]`` on one line;
- list holding any dict/list: expanded, one element per inner line;
- scalars and keys: ``json.dumps(..., ensure_ascii=False)``.

There is no trailing newline; ``hooks.format_patch_text`` adds one when the
original file had it. The legacy Max 8 layout (tab indent, ``"key" : value``)
is not reproduced.
"""

from __future__ import annotations

import json
import re

__all__ = ["dumps_max", "has_expanded_arrays"]

# A '[' followed by a newline and the start of a scalar: the json.dumps
# layout. A newline inside a JSON string is always escaped, so string
# payloads cannot match.
_EXPANDED_ARRAY_RE = re.compile(r'\[\r?\n[ \t]*(?:-?\d|"|true|false|null)')


def has_expanded_arrays(text: str) -> bool:
    """True when *text* holds a non-empty scalar array spread over lines.

    That is the ``json.dumps(indent=...)`` layout the framework used to
    write; MAX 9 writes scalar arrays inline.
    """
    return _EXPANDED_ARRAY_RE.search(text) is not None


def _key_str(key) -> str:
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
    return json.dumps(k, ensure_ascii=False)


def _is_container(value) -> bool:
    return isinstance(value, (dict, list, tuple))


def _dump(value, indent: str, level: int, out: list) -> None:
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
            out.append(inner + _key_str(k) + ": ")
            _dump(v, indent, level + 1, out)
        out.append("\n" + pad + "}")
        return
    if isinstance(value, (list, tuple)):
        if not value:
            out.append("[]")
            return
        if not any(_is_container(e) for e in value):
            out.append(
                "[ "
                + ", ".join(json.dumps(e, ensure_ascii=False) for e in value)
                + " ]"
            )
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
            _dump(e, indent, level + 1, out)
        out.append("\n" + pad + "]")
        return
    out.append(json.dumps(value, ensure_ascii=False))


def dumps_max(obj, indent: str = "    ") -> str:
    """Serialize *obj* in MAX 9's JSON layout (no trailing newline).

    Key order is kept, never sorted. ``json.loads(dumps_max(x)) == x``.

    Args:
        obj: A JSON-serializable value (normally a patcher dict).
        indent: One indentation step (MAX writes 4 spaces).

    Returns:
        The JSON text.
    """
    out: list[str] = []
    _dump(obj, indent, 0, out)
    return "".join(out)
