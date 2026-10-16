"""Atomic, mode-preserving file writes for the object-DB tooling (Q30 / I5, I6).

Stdlib only, and nothing from ``src.maxpat`` is imported, so both the audit
merger (``src/maxpat/audit/merger.py``) and the sync tool
(``tools/sync_max_bundle.py``) can share it without an import cycle.

* :func:`atomic_write_bytes` -- one file: temp file in the target's own
  directory, fsync, the target's existing mode (or ``0o666 & ~umask`` for a
  new file), then ``os.replace``. On failure the target is untouched and no
  temp file is left behind.
* :func:`atomic_write_many` -- several files, all or nothing: every temp file
  is written before any replace; if a replace fails, every target already
  replaced gets its original bytes and mode back (or is removed again if it
  did not exist), and the exception propagates.
* :func:`json_style` -- the ``(ensure_ascii, trailing_newline)`` pair with
  which ``json.dumps(data, indent=2)`` reproduces a file's bytes exactly.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Sequence, Tuple, Union

PathLike = Union[str, "os.PathLike[str]"]

_TEMP_PREFIX = ".atomic-"
_TEMP_SUFFIX = ".tmp"


def _umask_default() -> int:
    """``0o666 & ~umask``: the mode a plain ``open(path, "w")`` would create."""
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def _target_mode(target: Path) -> int:
    """The existing target's permission bits, or the umask default for a new file."""
    try:
        return stat.S_IMODE(os.stat(target).st_mode)
    except FileNotFoundError:
        return _umask_default()


def _write_temp(target: Path, payload: bytes, mode: int) -> str:
    """Write `payload` to a fsynced temp file beside `target` with `mode`; return its name."""
    handle, tmp_name = tempfile.mkstemp(
        prefix=_TEMP_PREFIX, suffix=_TEMP_SUFFIX, dir=str(target.parent)
    )
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, mode)
    except BaseException:
        _discard(tmp_name)
        raise
    return tmp_name


def _discard(tmp_name: str) -> None:
    try:
        os.unlink(tmp_name)
    except FileNotFoundError:
        pass


def atomic_write_bytes(path: PathLike, payload: bytes) -> None:
    """Replace `path` with `payload` atomically, keeping the file's mode.

    A new file gets ``0o666 & ~umask``. On any exception the target is left
    as it was and the temp file is removed.
    """
    target = Path(path)
    tmp_name = _write_temp(target, payload, _target_mode(target))
    try:
        os.replace(tmp_name, target)
    except BaseException:
        _discard(tmp_name)
        raise


def atomic_write_many(items: Sequence[Tuple[PathLike, bytes]]) -> None:
    """Write every ``(path, payload)`` or none of them.

    Phase 1 writes every temp file (each with its own target's mode) before
    any replace. Phase 2 replaces them in order, remembering each original's
    bytes and mode (or that it was absent). If any replace fails, the targets
    already replaced are restored, the remaining temp files are removed, and
    the exception re-raises.
    """
    staged: list[tuple[Path, str]] = []
    try:
        for path, payload in items:
            target = Path(path)
            staged.append((target, _write_temp(target, payload, _target_mode(target))))
    except BaseException:
        for _, tmp_name in staged:
            _discard(tmp_name)
        raise

    originals: list[tuple[Path, bytes | None, int | None]] = []
    done = 0
    try:
        for target, tmp_name in staged:
            if target.exists():
                original = (target, target.read_bytes(), stat.S_IMODE(os.stat(target).st_mode))
            else:
                original = (target, None, None)
            os.replace(tmp_name, target)
            originals.append(original)
            done += 1
    except BaseException:
        for _, tmp_name in staged[done:]:
            _discard(tmp_name)
        for target, raw, mode in reversed(originals):
            if raw is None:
                try:
                    os.unlink(target)
                except FileNotFoundError:
                    pass
            else:
                restored = _write_temp(target, raw, mode)
                try:
                    os.replace(restored, target)
                except BaseException:
                    _discard(restored)
                    raise
        raise


def json_style(raw: bytes, data) -> tuple[bool, bool] | None:
    """``(ensure_ascii, trailing_newline)`` that makes ``json.dumps(data, indent=2)`` equal `raw`.

    ensure_ascii False is tried first, so a pure-ASCII file (which reproduces
    both ways) prefers UTF-8 output. None when no combination reproduces it.
    """
    for ensure_ascii in (False, True):
        body = json.dumps(data, indent=2, ensure_ascii=ensure_ascii)
        for trailing_newline in (True, False):
            if (body + ("\n" if trailing_newline else "")).encode("utf-8") == raw:
                return ensure_ascii, trailing_newline
    return None
