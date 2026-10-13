"""Per-object I/O resolvers and the quote-aware box tokenizer (Q10).

Review 2026-10-11 finding C1: argument-dependent inlet/outlet counts were
wrong for everyday objects (``r foo`` got an inlet, ``sel 0`` one inlet,
``t "a b"`` two outlets). Section 2 S6 of the same review asks for
per-object resolver callables, checked against the help-box oracle
(``tools/audit_db.py --help-io``), instead of growing the string-formula
mini-language in ``overrides.json`` ``variable_io_rules``.

This module holds:

* :func:`split_box_text` / :func:`box_args` / :func:`normalize_args`: the
  tokenizer MAX applies to box text. Double quotes group words into one
  argument, a backslash makes the next character literal, and positional
  arguments stop at the first ``@attribute`` token.
* :data:`IO_RESOLVERS`: canonical object name -> resolver. A resolver takes
  ``(args, (default_inlets, default_outlets))`` -- the normalized positional
  args and the DB array lengths -- and returns ``(inlets, outlets)``.

Rules of the registry:

* Keys are **canonical** DB names; aliases (``r``, ``sel``, ``t``, ``b``)
  resolve through ``aliases.json`` before dispatch.
* A resolver wins over ``variable_io_rules``. ``ObjectDatabase`` refuses to
  load when one name has both (no silent ambiguity).
* Every resolver docstring cites the MAX-saved help box(es) it reproduces.

This module never imports ``src.maxpat.db_lookup`` (db_lookup imports this
module; the reverse import would be a cycle).
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

IoResolver = Callable[[List[str], Tuple[int, int]], Tuple[int, int]]


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def split_box_text(text: str) -> list[str]:
    """Split box text into MAX tokens, respecting quotes and backslash escapes.

    * Whitespace (spaces, tabs, newlines) outside double quotes separates
      tokens.
    * A double quote toggles the quoted state and is kept in the token, so
      ``t "a b" c`` -> ``['t', '"a b"', 'c']``.
    * A backslash makes the next character literal and is kept in the token:
      ``\\"`` does not toggle quoting and ``\\ `` (escaped space) does not
      split. A trailing backslash is kept as-is.
    * An unbalanced quote runs to the end of the text as one token.
    * Empty or whitespace-only text returns ``[]``. Never raises: a
      non-string input is converted with ``str()`` (``None`` -> ``[]``).
    """
    if text is None:
        return []
    if not isinstance(text, str):
        text = str(text)
    tokens: list[str] = []
    cur: list[str] = []
    in_token = False
    quoted = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            cur.append(ch)
            if i + 1 < n:
                cur.append(text[i + 1])
                i += 1
            in_token = True
        elif ch == '"':
            quoted = not quoted
            cur.append(ch)
            in_token = True
        elif ch.isspace() and not quoted:
            if in_token:
                tokens.append("".join(cur))
                cur = []
                in_token = False
        else:
            cur.append(ch)
            in_token = True
        i += 1
    if in_token:
        tokens.append("".join(cur))
    return tokens


def _positional(tokens: list[str]) -> list[str]:
    """Tokens up to (not including) the first one starting with ``@``."""
    out: list[str] = []
    for tok in tokens:
        if tok.startswith("@"):
            break
        out.append(tok)
    return out


def box_args(text: str) -> tuple[str, list[str]]:
    """Split newobj text into ``(name, positional args)``.

    The name is token 0 of :func:`split_box_text`; the args are the following
    tokens up to the first ``@attribute`` token. Empty text -> ``("", [])``.
    """
    tokens = split_box_text(text)
    if not tokens:
        return ("", [])
    return (tokens[0], _positional(tokens[1:]))


def normalize_args(args) -> list[str]:
    """Re-tokenize an args list the way MAX reads the box text.

    The elements are joined with single spaces (each through ``str()``) and
    split again with :func:`split_box_text`, then truncated at the first
    ``@`` token. Pre-split quoted words (``['"LCD', 'Text', '(Inactive)"']``)
    and the single quoted token give the same one-element list, so callers
    may pass either form. ``None`` -> ``[]``.
    """
    if args is None:
        return []
    if isinstance(args, str):
        joined = args
    else:
        joined = " ".join(str(a) for a in args)
    return _positional(split_box_text(joined))


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def _receive(args: list[str], defaults: tuple[int, int]) -> tuple[int, int]:
    """receive / r: a named receive has no inlet; bare receive keeps one.

    MAX-saved boxes: ``r todrive`` = (0,1) (C74/help/jitter/
    jit.anim.drive.maxhelp), ``receive bem`` = (0,1) (C74/help/max/
    forward.maxhelp), ``receive`` = (1,1) (C74/help/max/receive.maxhelp;
    the inlet takes ``set <name>``).
    """
    if args:
        return (0, 1)
    return defaults


IO_RESOLVERS: Dict[str, IoResolver] = {
    "receive": _receive,
}
