"""Max for Live device builder and .amxd codec (quick 261022-pqu, fix-plan Q40).

EXPERIMENTAL -- not yet confirmed in Live. The combined Q15 + Q40 Live check
(``.planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/
q40-live-check.amxd`` and the checklist in that task's SUMMARY) is pending;
until the user confirms it, treat every device built or exported here as
unverified in Live.

Provides:
- The .amxd codec: :class:`AmxdFile`, :func:`parse_amxd`, :func:`build_amxd`,
  :func:`encode_payload`, :func:`decode_payload`.
- :func:`export_amxd`: write an .amxd next to (or from) a .maxpat, which stays
  the editable source of truth.
- Parameter resolution: :func:`name_tokens`, :func:`infer_type_unit`,
  :func:`unique_shortnames`, :func:`resolve_param_specs`.
- The three-kind device skeleton behind ``Patcher.add_m4l_device``:
  :class:`M4LDevice`, :func:`build_m4l_device` (reuses existing device I/O,
  never doubles it; quick 261022-ud6 BL-01).
- Duplicated device I/O detection: :func:`find_duplicate_device_io` and the
  critic hook :func:`duplicate_device_io_results`.

Evidence (RESEARCH for 261022-pqu):
- Byte format: an .amxd is a chunk stream ``[tag][uint32 LE length][payload]``
  -- ``ampf`` (kind code), ``meta`` (uint32 flags, 0 for editable devices),
  ``ptch`` (UTF-8 patcher JSON that Max ends with ``\\n\\0``). Checked on 309
  real files, including Live 12's "Max Devices" templates, Max.app's
  fourin_fourout.amxd and the framework's own kicksynth-m4l.amxd (git
  494c2e64), which Live 12.3.6 loaded. See the comment block in
  m4l_constants.py.
- Wiring per kind is copied from Live 12's templates: audio effect plugin~
  0->0 and 1->1 into plugout~; MIDI effect midiin -> midiout; instrument a
  lone midiin plus an unwired plugout~. plugin~/plugout~ are always bare.
- Parameter type/unit inference follows parameters.maxref.xml (the Int type
  holds 256 values; wider integer ranges use Float type with Int unit style)
  and bundle statistics of (type, unitstyle) against range and name.

Import-cycle safety: only stdlib, m4l_constants, maxjson and atomic_io are
imported at module level; m4l_polish, the M4L critic and hooks are imported
inside the functions that need them.
"""

from __future__ import annotations

import json
import math
import os
import re
import struct
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.maxpat.atomic_io import atomic_write_bytes
from src.maxpat.m4l_constants import (
    AMXD_CHUNK_HEADER,
    AMXD_MAGIC,
    AMXD_META_MARKER,
    AMXD_PATCH_MARKER,
    AMXD_PAYLOAD_TERMINATOR,
    AMXD_TYPE_AUDIO_EFFECT,
    AMXD_TYPE_INSTRUMENT,
    AMXD_TYPE_MIDI_EFFECT,
    ModMode,
    ParamType,
    UnitStyle,
)
from src.maxpat.maxjson import dumps_max

__all__ = [
    "KIND_CODES",
    "KIND_NAMES",
    "AmxdFile",
    "parse_amxd",
    "build_amxd",
    "encode_payload",
    "decode_payload",
    "export_amxd",
    "name_tokens",
    "infer_type_unit",
    "unique_shortnames",
    "resolve_param_specs",
    "M4LDevice",
    "build_m4l_device",
    "DEVICE_SINGLETON_NAMES",
    "find_duplicate_device_io",
    "duplicate_device_io_results",
]

# ---------------------------------------------------------------------------
# .amxd codec
# ---------------------------------------------------------------------------

KIND_CODES: dict[str, bytes] = {
    "audio_effect": AMXD_TYPE_AUDIO_EFFECT,
    "instrument": AMXD_TYPE_INSTRUMENT,
    "midi_effect": AMXD_TYPE_MIDI_EFFECT,
}
KIND_NAMES: dict[bytes, str] = {code: kind for kind, code in KIND_CODES.items()}

_CIPH = b"ciph"
_FROZEN_PREFIX = b"mx@c"
_CHUNK_HEADER_SIZE = struct.calcsize(AMXD_CHUNK_HEADER)
_FROZEN_MSG = "frozen/encrypted device ({why}) -- cannot export or edit it"


@dataclass(frozen=True)
class AmxdFile:
    """One parsed .amxd: kind code, meta flags (None when absent), raw ptch payload."""

    code: bytes
    meta: "int | None"
    payload: bytes

    @property
    def kind(self) -> str:
        """Device kind name ("audio_effect" / "instrument" / "midi_effect")."""
        return KIND_NAMES[self.code]


def _read_chunk(data: bytes, pos: int) -> tuple[bytes, bytes, int]:
    """(tag, payload, next offset) of the chunk at *pos*; bounds-checked."""
    if len(data) - pos < _CHUNK_HEADER_SIZE:
        raise ValueError(
            f"truncated chunk header at offset {pos} ({len(data) - pos} bytes left)"
        )
    tag, length = struct.unpack_from(AMXD_CHUNK_HEADER, data, pos)
    start = pos + _CHUNK_HEADER_SIZE
    end = start + length
    if end > len(data):
        raise ValueError(
            f"chunk {tag!r} at offset {pos} has length {length}, which runs past "
            f"the end of the file ({len(data)} bytes)"
        )
    return tag, data[start:end], end


def _code_for(kind_or_code: "str | bytes") -> bytes:
    if isinstance(kind_or_code, (bytes, bytearray)):
        code = bytes(kind_or_code)
        if code not in KIND_NAMES:
            raise ValueError(
                f"unknown device kind code {code!r}; expected one of "
                f"{sorted(KIND_NAMES)}"
            )
        return code
    if kind_or_code not in KIND_CODES:
        raise ValueError(
            f"unknown device kind {kind_or_code!r}; expected one of {sorted(KIND_CODES)}"
        )
    return KIND_CODES[kind_or_code]


def parse_amxd(data: bytes) -> AmxdFile:
    """Parse an .amxd byte string chunk by chunk.

    Never parses through ``AMXD_HEADER_FORMAT`` (its ``4x`` drops the meta
    payload) and never evaluates the payload. Every chunk length is checked
    against the bytes that remain.

    Raises:
        ValueError: the first chunk is not ``ampf`` (length 4, a known kind
            code: Live 12 MIDI Tool kinds ``natt``/``nagg`` are refused); a
            ``ciph`` chunk or a ``ptch`` payload starting ``mx@c`` (frozen or
            encrypted device); a truncated chunk; an unexpected chunk; no
            ``ptch`` chunk; bytes after the ``ptch`` chunk.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"parse_amxd expects bytes, got {type(data).__name__}")
    data = bytes(data)

    tag, payload, pos = _read_chunk(data, 0)
    if tag != AMXD_MAGIC:
        raise ValueError(f"not an .amxd: first chunk is {tag!r}, expected {AMXD_MAGIC!r}")
    if len(payload) != 4:
        raise ValueError(f"ampf chunk has length {len(payload)}, expected 4")
    if payload not in KIND_NAMES:
        raise ValueError(
            f"unknown device kind code {payload!r} (supported: aaaa, iiii, mmmm; "
            f"Live 12 MIDI Tools are out of scope)"
        )
    code = payload

    meta: "int | None" = None
    seen_meta = False
    patch: "bytes | None" = None
    while pos < len(data):
        offset = pos
        tag, payload, pos = _read_chunk(data, pos)
        if tag == _CIPH:
            raise ValueError(_FROZEN_MSG.format(why="ciph chunk"))
        if tag == AMXD_META_MARKER and not seen_meta:
            if len(payload) != 4:
                raise ValueError(f"meta chunk has length {len(payload)}, expected 4")
            meta = struct.unpack("<I", payload)[0]
            seen_meta = True
            continue
        if tag == AMXD_PATCH_MARKER:
            if payload.startswith(_FROZEN_PREFIX):
                raise ValueError(_FROZEN_MSG.format(why="mx@c payload"))
            patch = payload
            if pos != len(data):
                raise ValueError(
                    f"{len(data) - pos} trailing bytes after the ptch chunk"
                )
            break
        raise ValueError(f"unexpected chunk {tag!r} at offset {offset}")

    if patch is None:
        raise ValueError("no ptch chunk: the file holds no patcher")
    return AmxdFile(code=code, meta=meta, payload=patch)


def build_amxd(kind_or_code: "str | bytes", payload: bytes, meta: "int | None" = 0) -> bytes:
    """Assemble an .amxd: ``ampf`` chunk, ``meta`` chunk (omitted when None), ``ptch`` chunk.

    ``build_amxd(f.code, f.payload, f.meta)`` reproduces a parsed file byte
    for byte. With ``meta=0`` the first 32 bytes equal
    ``struct.pack(AMXD_HEADER_FORMAT, ...)``.

    Raises:
        ValueError: unknown kind, or *meta* not None and not an int in
            ``0 <= meta < 2**32`` (the chunk is a uint32; a bool is refused).
    """
    code = _code_for(kind_or_code)
    if meta is not None and (not _is_int(meta) or not 0 <= meta < 2 ** 32):
        raise ValueError(f"meta must be None or an int in [0, 2**32), got {meta!r}")
    payload = bytes(payload)
    out = struct.pack(AMXD_CHUNK_HEADER, AMXD_MAGIC, len(code)) + code
    if meta is not None:
        out += struct.pack(AMXD_CHUNK_HEADER, AMXD_META_MARKER, 4) + struct.pack("<I", meta)
    out += struct.pack(AMXD_CHUNK_HEADER, AMXD_PATCH_MARKER, len(payload)) + payload
    return out


def encode_payload(patch_dict: dict) -> bytes:
    """``dumps_max(patch_dict)`` as UTF-8 plus Max's ``\\n\\0`` terminator."""
    if not isinstance(patch_dict, dict) or not isinstance(patch_dict.get("patcher"), dict):
        raise ValueError('encode_payload expects a patch dict with a "patcher" dict')
    return dumps_max(patch_dict).encode("utf-8") + AMXD_PAYLOAD_TERMINATOR


def decode_payload(payload: bytes) -> dict:
    """Decode a ``ptch`` payload: strip ONE trailing NUL, strict UTF-8, ``json.loads``.

    Raises:
        ValueError: frozen payload, invalid UTF-8, invalid JSON, or a JSON
            value that is not an object.
    """
    payload = bytes(payload)
    if payload.startswith(_FROZEN_PREFIX):
        raise ValueError(_FROZEN_MSG.format(why="mx@c payload"))
    if payload.endswith(b"\x00"):
        payload = payload[:-1]
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"ptch payload is not valid UTF-8: {exc}") from None
    value = json.loads(text)  # JSONDecodeError is a ValueError
    if not isinstance(value, dict):
        raise ValueError(f"ptch payload is JSON {type(value).__name__}, expected an object")
    return value


def export_amxd(
    patcher_or_path: Any,
    out_path: "str | os.PathLike | None" = None,
    kind: "str | None" = None,
) -> Path:
    """Write an .amxd from a Patcher, a patch dict or a .maxpat path. EXPERIMENTAL.

    EXPERIMENTAL -- not yet confirmed in Live (Q15/Q40 Live check pending).

    The .maxpat is the source of truth: save it through
    ``save_patch_roundtrip`` first (save gate, Rule #7), then export. The
    .amxd is a derived binary; this function never touches the .maxpat.

    Layout: ``ampf`` (kind code) + ``meta`` (0) + ``ptch``
    (``dumps_max`` JSON + ``\\n\\0``), the form Max writes for an editable
    device. No ``project`` block is injected.

    Args:
        patcher_or_path: A Patcher (``to_dict()`` is used), a patch dict, or a
            str/Path to a .maxpat file.
        out_path: Target file; must end in ``.amxd``. Defaults to the
            .maxpat path with an ``.amxd`` suffix (required for a Patcher or
            dict).
        kind: "instrument", "audio_effect" or "midi_effect". None uses
            ``detect_m4l_device_type``.

    Returns:
        The written path. Under ``patches/<project>/`` the .amxd alone is
        auto-committed; elsewhere the auto-commit warns and you commit it
        yourself with an explicit path.

    Raises:
        ValueError: out_path missing or not ``.amxd``; kind unknown or not
            detectable; the patch is a live.thisdevice-only helper
            abstraction and no explicit kind was given;
            ``patcher.project.amxdtype`` disagrees with the kind.
            Nothing is written.
    """
    src_path: "Path | None" = None
    if isinstance(patcher_or_path, (str, os.PathLike)):
        src_path = Path(patcher_or_path)
        patch = json.loads(src_path.read_text(encoding="utf-8"))
    elif isinstance(patcher_or_path, dict):
        patch = patcher_or_path
    elif hasattr(patcher_or_path, "to_dict"):
        patch = patcher_or_path.to_dict()
    else:
        raise TypeError(
            f"export_amxd expects a Patcher, a patch dict or a .maxpat path, "
            f"got {type(patcher_or_path).__name__}"
        )

    if out_path is None:
        if src_path is None:
            raise ValueError("out_path is required when exporting a Patcher or a dict")
        out = src_path.with_suffix(".amxd")
    else:
        out = Path(out_path)
    if out.suffix.lower() != ".amxd":
        raise ValueError(f"out_path must end in .amxd, got {str(out)!r}")

    from src.maxpat.critics.m4l_critic import M4L_ABSTRACTION, detect_m4l_device_type

    detected = detect_m4l_device_type(patch)
    if kind is None and detected == M4L_ABSTRACTION or kind == M4L_ABSTRACTION:
        # quick 261022-ud6 WP7a: say why instead of "unknown device kind".
        raise ValueError(
            "a live.thisdevice-only patch (no plugin~, plugout~, midiin or "
            "midiout) is a helper abstraction, not a device: export the device "
            "that uses it, or pass kind='audio_effect' / 'instrument' / "
            "'midi_effect' explicitly"
        )
    if kind is None:
        kind = detected
        if kind is None:
            raise ValueError(
                "cannot detect the device kind (no plugin~, plugout~ or "
                "live.thisdevice); pass kind= explicitly"
            )
    elif kind in KIND_CODES and detected in KIND_CODES and detected != kind:
        # Q40 review IN-01: an explicit kind is honoured, but a patch whose
        # contents say otherwise (plugin~ exported as an instrument) gets a
        # warning -- detection is a heuristic, so it never refuses.
        warnings.warn(
            f"export_amxd: kind {kind!r} disagrees with the patch contents, which "
            f"look like an {detected!r} device (detect_m4l_device_type); Live "
            f"loads the .amxd as {kind!r}",
            UserWarning,
            stacklevel=2,
        )
    code = _code_for(kind)

    patcher = patch.get("patcher") if isinstance(patch, dict) else None
    project = patcher.get("project") if isinstance(patcher, dict) else None
    if isinstance(project, dict) and "amxdtype" in project:
        expected = int.from_bytes(code, "big")
        if project["amxdtype"] != expected:
            raise ValueError(
                f"patcher.project.amxdtype {project['amxdtype']!r} disagrees with "
                f"kind {kind!r} ({expected})"
            )

    data = build_amxd(code, encode_payload(patch), 0)
    atomic_write_bytes(out, data)

    from src.maxpat.hooks import _auto_commit_saved_file

    _auto_commit_saved_file(out)
    return out


# ---------------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------------

_UNIT_TOKENS = {"ms": UnitStyle.TIME, "hz": UnitStyle.HERTZ, "db": UnitStyle.DECIBEL}
_TIME_WORDS = frozenset({"time", "attack", "decay", "release", "delay", "length"})
_HERTZ_WORDS = frozenset({"freq", "frequency", "cutoff"})
_LEVEL_WORDS = frozenset({"gain", "volume", "level"})
_SEMITONE_WORDS = frozenset({"semi", "semitone", "semitones", "transpose"})
_CAMEL_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")

# Live's Int parameter type holds 256 values (parameters.maxref.xml "Type").
_INT_TYPE_MAX_SPAN = 255
# Auto short names fit Push's display (m4l_polish._abbreviate_shortname).
SHORTNAME_MAX = 8

_REQUIRED_KEYS = ("name", "min", "max", "default")
_OPTIONAL_KEYS = ("unit", "type", "steps", "short_name", "varname", "param_connect", "modmode")
_UNIT_ALIASES = {
    "ms": UnitStyle.TIME,
    "hz": UnitStyle.HERTZ,
    "db": UnitStyle.DECIBEL,
    "%": UnitStyle.PERCENT,
}


def name_tokens(name: str) -> list[str]:
    """Lowercase whole-word tokens of a parameter name.

    Splits on non-alphanumerics; a piece that is exactly ms/hz/db (any case)
    stays one token, others are split on camelCase and digit runs
    (``cutoffHz`` -> cutoff, hz; ``freq1`` -> freq, 1).
    """
    tokens: list[str] = []
    for piece in re.split(r"[^0-9A-Za-z]+", name):
        if not piece:
            continue
        if piece.lower() in _UNIT_TOKENS:
            tokens.append(piece.lower())
            continue
        tokens.extend(t.lower() for t in _CAMEL_RE.findall(piece))
    return tokens


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def infer_type_unit(name: str, mn: float, mx: float, default: float) -> tuple[ParamType, UnitStyle]:
    """Infer ``(parameter_type, parameter_unitstyle)`` from a name and range.

    Whole tokens only, never substrings ("harmonics" is not "ms"). Unit, first
    match wins: token ms -> Time, hz -> Hertz, db -> deciBel; a non-integer
    range inside [0, 1] -> Float; time/attack/decay/release/delay/length ->
    Time; freq/frequency/cutoff -> Hertz; gain/volume/level with min < 0 ->
    deciBel; pan -> Pan; semi/semitone(s)/transpose -> Semitones; an all-int
    (min, max, default) -> Int; else Float. Type: Int when all three are
    Python ints and the span is <= 255, else Float (parameters.maxref.xml:
    wider integer ranges use Float type with Int unit style).
    """
    toks = set(name_tokens(name))
    all_int = _is_int(mn) and _is_int(mx) and _is_int(default)
    ptype = ParamType.INT if all_int and (mx - mn) <= _INT_TYPE_MAX_SPAN else ParamType.FLOAT

    if "ms" in toks:
        unit = UnitStyle.TIME
    elif "hz" in toks:
        unit = UnitStyle.HERTZ
    elif "db" in toks:
        unit = UnitStyle.DECIBEL
    elif not all_int and 0 <= mn and mx <= 1:
        unit = UnitStyle.FLOAT
    elif toks & _TIME_WORDS:
        unit = UnitStyle.TIME
    elif toks & _HERTZ_WORDS:
        unit = UnitStyle.HERTZ
    elif toks & _LEVEL_WORDS and mn < 0:
        unit = UnitStyle.DECIBEL
    elif "pan" in toks:
        unit = UnitStyle.PAN
    elif toks & _SEMITONE_WORDS:
        unit = UnitStyle.SEMITONES
    elif all_int:
        unit = UnitStyle.INT
    else:
        unit = UnitStyle.FLOAT
    return ptype, unit


def unique_shortnames(longnames: list[str], explicit: list, *, reserved=()) -> list[str]:
    """Short names: explicit ones verbatim, auto ones abbreviated and de-duplicated.

    An auto name is ``m4l_polish._abbreviate_shortname(name, 8)``; when that
    is already taken (by an explicit name, an earlier auto name or one of
    *reserved* -- the short names already in the patcher) it is trimmed and
    suffixed 2, 3, ... within 8 characters ("Amount", "Amount2"). Explicit
    names are never altered and never reused by an auto name.
    """
    from src.maxpat.m4l_polish import _abbreviate_shortname

    if len(longnames) != len(explicit):
        raise ValueError("longnames and explicit must have the same length")
    taken = {s for s in explicit if s} | {s for s in reserved if s}
    out: list[str] = []
    for longname, given in zip(longnames, explicit):
        if given:
            out.append(given)
            continue
        base = _abbreviate_shortname(longname, SHORTNAME_MAX)
        cand = base
        k = 2
        while cand in taken:
            suffix = str(k)
            cand = base[: SHORTNAME_MAX - len(suffix)].rstrip() + suffix
            k += 1
        taken.add(cand)
        out.append(cand)
    return out


def _coerce_member(value: Any, enum_cls, key: str, aliases: dict, refused: tuple):
    if isinstance(value, bool):
        raise ValueError(f"{key} must not be a bool")
    member = None
    if isinstance(value, enum_cls):
        member = value
    elif isinstance(value, int):
        try:
            member = enum_cls(value)
        except ValueError:
            raise ValueError(f"{key} {value!r} is not a valid {enum_cls.__name__}") from None
    elif isinstance(value, str):
        text = value.strip()
        if text.lower() in aliases:
            member = aliases[text.lower()]
        else:
            try:
                member = enum_cls[text.upper()]
            except KeyError:
                raise ValueError(f"{key} {value!r} is not a valid {enum_cls.__name__}") from None
    else:
        raise ValueError(f"{key} must be a {enum_cls.__name__}, an int or a name, got {value!r}")
    if member in refused:
        raise ValueError(
            f"{key} {member.name} is not supported by add_m4l_device "
            f"(out of scope for Q40)"
        )
    return member


def _number(value: Any, key: str, name: str) -> "int | float":
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"param {name!r}: {key} must be a number, got {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"param {name!r}: {key} must be finite, got {value!r}")
    return value


def _derive_varname(name: str) -> str:
    if name.isidentifier():
        return name
    return re.sub(r"\W+", "_", name).strip("_").lower() or "param"


def _integral(value) -> bool:
    return _is_int(value) or (isinstance(value, float) and value.is_integer())


def resolve_param_specs(
    params: list,
    *,
    modmode: "ModMode | int | str" = ModMode.NONE,
    existing_longnames=(),
    existing_shortnames=(),
) -> list[dict]:
    """Validate parameter spec dicts and resolve inferred metadata.

    Each spec: required ``name``, ``min``, ``max``, ``default``; optional
    ``unit``, ``type``, ``steps``, ``short_name``, ``varname``,
    ``param_connect``, ``modmode``. Explicit keys always win over inference
    (:func:`infer_type_unit`); short names come from
    :func:`unique_shortnames` (auto names avoid *existing_shortnames*);
    ``varname`` defaults to the name when it is a valid identifier, else its
    lowercased ``\\W+`` -> ``_`` form.

    *existing_longnames* / *existing_shortnames* are the parameter names
    already in the target patcher (``build_m4l_device`` passes them): a spec
    name equal to an existing longname, or an explicit short name equal to
    an existing short name, is refused (review WR-01) -- it would give a
    blocking ``parameter_uniqueness`` finding or two parameters with one
    label.

    Returns:
        One dict per spec with keys name, min, max, default (as given),
        type, unit, modmode (ints), steps (int or None), short_name,
        varname, param_connect (str or None).

    Raises:
        ValueError: non-dict spec, unknown or missing keys, empty name,
            duplicate names, varnames or explicit short names, a name or
            explicit short name already used in the patcher, non-numeric or
            bool bounds, min >= max, default outside [min, max], steps < 2,
            an Enum/Blob type or a Custom unit.

    Warns (UserWarning; explicit keys still win, Q40 review IN-02): an
    explicit Int type with a non-integral min/max/default or a span over
    255 (Live's Int type holds 256 values).
    """
    default_mod = _coerce_member(modmode, ModMode, "modmode", {}, ())
    resolved: list[dict] = []
    for spec in params:
        if not isinstance(spec, dict):
            raise ValueError(f"each param must be a dict, got {spec!r}")
        unknown = [k for k in spec if k not in _REQUIRED_KEYS + _OPTIONAL_KEYS]
        if unknown:
            raise ValueError(f"param {spec.get('name')!r}: unknown keys {unknown}")
        missing = [k for k in _REQUIRED_KEYS if k not in spec]
        if missing:
            raise ValueError(f"param {spec.get('name')!r}: missing keys {missing}")
        name = spec["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"param name must be a non-empty string, got {name!r}")
        mn = _number(spec["min"], "min", name)
        mx = _number(spec["max"], "max", name)
        default = _number(spec["default"], "default", name)
        if not mn < mx:
            raise ValueError(f"param {name!r}: min {mn!r} must be < max {mx!r}")
        if not mn <= default <= mx:
            raise ValueError(f"param {name!r}: default {default!r} outside [{mn!r}, {mx!r}]")

        inferred_type, inferred_unit = infer_type_unit(name, mn, mx, default)
        ptype = (
            _coerce_member(spec["type"], ParamType, "type", {},
                           (ParamType.ENUM, ParamType.BLOB))
            if spec.get("type") is not None else inferred_type
        )
        unit = (
            _coerce_member(spec["unit"], UnitStyle, "unit", _UNIT_ALIASES, (UnitStyle.CUSTOM,))
            if spec.get("unit") is not None else inferred_unit
        )
        mod = (
            _coerce_member(spec["modmode"], ModMode, "modmode", {}, ())
            if spec.get("modmode") is not None else default_mod
        )
        # Explicit keys win, but an explicit Int type that Live cannot hold
        # is reported now rather than only by the critics (Q40 review IN-02).
        if spec.get("type") is not None and ptype == ParamType.INT:
            if not (_integral(mn) and _integral(mx) and _integral(default)):
                warnings.warn(
                    f"param {name!r}: explicit type Int with non-integral "
                    f"min/max/default {mn!r}/{mx!r}/{default!r} -- Live rounds them; "
                    f"use type Float",
                    UserWarning,
                    stacklevel=3,
                )
            elif mx - mn > _INT_TYPE_MAX_SPAN:
                warnings.warn(
                    f"param {name!r}: explicit type Int holds 256 values but the "
                    f"range spans {mn!r}..{mx!r} -- Live clips it; use type Float "
                    f"with unit Int",
                    UserWarning,
                    stacklevel=3,
                )

        steps = spec.get("steps")
        if steps is not None and (not _is_int(steps) or steps < 2):
            raise ValueError(f"param {name!r}: steps must be an int >= 2, got {steps!r}")

        short = spec.get("short_name")
        if short is not None and (not isinstance(short, str) or not short.strip()):
            raise ValueError(f"param {name!r}: short_name must be a non-empty string")
        varname = spec.get("varname")
        if varname is None:
            varname = _derive_varname(name)
        elif not isinstance(varname, str) or not varname.strip():
            raise ValueError(f"param {name!r}: varname must be a non-empty string")
        connect = spec.get("param_connect")
        if connect is not None and (not isinstance(connect, str) or not connect.strip()):
            raise ValueError(f"param {name!r}: param_connect must be a non-empty string")

        resolved.append({
            "name": name,
            "min": mn,
            "max": mx,
            "default": default,
            "type": int(ptype),
            "unit": int(unit),
            "modmode": int(mod),
            "steps": steps,
            "short_name": short,
            "varname": varname,
            "param_connect": connect,
        })

    for key, label in (("name", "name"), ("varname", "varname"), ("short_name", "short name")):
        seen: set = set()
        for r in resolved:
            if r[key] is None:
                continue
            if r[key] in seen:
                raise ValueError(f"duplicate parameter {label} {r[key]!r}")
            seen.add(r[key])

    taken_long = set(existing_longnames)
    clash = [r["name"] for r in resolved if r["name"] in taken_long]
    if clash:
        raise ValueError(
            f"parameter name(s) {clash} already used by a parameter in this patcher "
            f"(parameter_longname must be unique in a device); pick another name"
        )
    taken_short = set(existing_shortnames)
    clash = [r["short_name"] for r in resolved if r["short_name"] in taken_short]
    if clash:
        raise ValueError(
            f"explicit short name(s) {clash} already used by a parameter in this "
            f"patcher; pick another short_name"
        )

    shorts = unique_shortnames([r["name"] for r in resolved], [r["short_name"] for r in resolved],
                               reserved=taken_short)
    for r, short in zip(resolved, shorts):
        r["short_name"] = short
    return resolved


# ---------------------------------------------------------------------------
# Device skeleton
# ---------------------------------------------------------------------------

# Live's device view is 169 px tall (template openrect [0, 0, 0, 169] and its
# "Device vertical limit" comment at y 170).
DEVICE_HEIGHT = 169.0
# Bundle live.dial default size; 8 px margin, 52 px column and 56 px row pitch.
_DIAL_W, _DIAL_H = 44.0, 48.0
_GRID_MARGIN, _GRID_DX, _GRID_DY = 8.0, 52.0, 56.0
_GRID_MAX_ROWS = 3


@dataclass
class M4LDevice:
    """Boxes created by :func:`build_m4l_device` (unused roles are None)."""

    kind: str
    plugin: Any = None
    plugout: Any = None
    midiin: Any = None
    midiout: Any = None
    thisdevice: Any = None
    init_trigger: Any = None
    dials: list = field(default_factory=list)
    banks: Any = None


def _check_endpoint(patcher, endpoint, label: str):
    if not (isinstance(endpoint, (tuple, list)) and len(endpoint) == 2):
        raise ValueError(f"{label} must be (Box, outlet), got {endpoint!r}")
    box, outlet = endpoint
    if not any(b is box for b in patcher.boxes):
        raise ValueError(f"{label} box {box!r} is not a box of this patcher")
    if not _is_int(outlet) or not 0 <= outlet < box.numoutlets:
        raise ValueError(
            f"{label} outlet {outlet!r} out of range for {box.name} ({box.numoutlets} outlets)"
        )
    return box, outlet


def _normalize_source(patcher, source, label: str, *, allow_pair: bool):
    """[(box, outlet)] for a single source, [(L), (R)] for a stereo pair, or None."""
    if source is None:
        return None
    if (
        allow_pair
        and isinstance(source, (tuple, list))
        and len(source) == 2
        and all(isinstance(s, (tuple, list)) for s in source)
    ):
        return [_check_endpoint(patcher, s, label) for s in source]
    return [_check_endpoint(patcher, source, label)]


def _presentation_cols(n: int) -> int:
    if n <= 8 * _GRID_MAX_ROWS:
        return min(n, 8)
    return -(-n // _GRID_MAX_ROWS)


def existing_varnames(patcher) -> set:
    """Scripting names (``varname``) already used by top-level boxes of *patcher*."""
    return {
        v for v in (b.extra_attrs.get("varname") for b in patcher.boxes)
        if isinstance(v, str) and v
    }


def check_varname_collisions(patcher, varnames, *, label: str = "param") -> None:
    """Raise ValueError if any of *varnames* is already a box varname in *patcher*.

    ``param_connect`` resolves its target by varname, so a duplicate makes
    the binding ambiguous (review WR-02).
    """
    taken = existing_varnames(patcher)
    clash = sorted(v for v in varnames if v in taken)
    if clash:
        raise ValueError(
            f"{label} varname(s) {clash} already used by a box in this patcher; "
            f"pass a distinct varname"
        )


def _existing_param_valueofs(patcher) -> list:
    """valueof dicts of live.* parameters already in *patcher* (recursive, box order)."""
    from src.maxpat.m4l_polish import _collect_live_controls

    out = []
    for box in _collect_live_controls(patcher.to_dict()["patcher"]["boxes"]):
        valueof = (box.get("saved_attribute_attributes") or {}).get("valueof") or {}
        if isinstance(valueof, dict):
            out.append(valueof)
    return out


def _existing_param_names(patcher, key: str) -> list:
    names = []
    for valueof in _existing_param_valueofs(patcher):
        name = valueof.get(key)
        if isinstance(name, str) and name and name not in names:
            names.append(name)
    return names


def _existing_param_longnames(patcher) -> list:
    """Longnames of live.* parameters already in *patcher* (recursive, box order)."""
    return _existing_param_names(patcher, "parameter_longname")


def _presentation_extent(patcher) -> "tuple[float, bool]":
    """(right edge of existing presentation boxes, any present)."""
    right, found = 0.0, False
    for b in patcher.boxes:
        if not b.presentation:
            continue
        rect = b.presentation_rect
        if isinstance(rect, (list, tuple)) and len(rect) == 4:
            right = max(right, float(rect[0]) + float(rect[2]))
            found = True
    return right, found


# ---------------------------------------------------------------------------
# Device I/O: reuse and duplicate detection (review BL-01, quick 261022-ud6)
# ---------------------------------------------------------------------------

# Boxes a device has exactly one of; a second one doubles the audio path
# (plugin~ / plugout~) or the init chain (live.thisdevice). The Q40 critic
# hook reports them (duplicate_device_io_results).
DEVICE_SINGLETON_NAMES = ("plugin~", "plugout~", "live.thisdevice")

_KIND_IO = {
    "audio_effect": ("plugin~", "plugout~"),
    "instrument": ("midiin", "plugout~"),
    "midi_effect": ("midiin", "midiout"),
}
_TRIGGER_NAMES = ("t", "trigger")


def _dict_box_name(box: dict) -> "str | None":
    maxclass = box.get("maxclass")
    if maxclass == "newobj":
        text = box.get("text")
        if isinstance(text, str) and text.split():
            return text.split()[0]
        return None
    return maxclass if isinstance(maxclass, str) else None


def find_duplicate_device_io(patch_dict) -> dict:
    """``{name: [box ids]}`` for each of :data:`DEVICE_SINGLETON_NAMES` that
    appears more than once in the TOP scope of *patch_dict*.

    A device needs one ``plugin~``, one ``plugout~`` and one
    ``live.thisdevice``: two ``plugin~ -> plugout~`` pass-throughs double the
    dry signal (+6 dB) and two ``live.thisdevice`` init chains bang every
    dial twice (review BL-01). Pure and read-only; junk input gives ``{}``.
    """
    patcher = patch_dict.get("patcher") if isinstance(patch_dict, dict) else None
    boxes = patcher.get("boxes") if isinstance(patcher, dict) else None
    if not isinstance(boxes, list):
        return {}
    found: dict = {}
    for entry in boxes:
        box = entry.get("box") if isinstance(entry, dict) else None
        if not isinstance(box, dict):
            continue
        name = _dict_box_name(box)
        if name in DEVICE_SINGLETON_NAMES:
            found.setdefault(name, []).append(str(box.get("id", "?")))
    return {name: ids for name, ids in found.items() if len(ids) > 1}


def duplicate_device_io_results(patch_dict) -> list:
    """:func:`find_duplicate_device_io` as warning ``CriticResult`` s.

    Critic hook for ``m4l_critic.review_m4l`` (rule ``duplicate_device_io``,
    severity warning, top scope only).
    """
    from src.maxpat.critics.base import CriticResult, finding_ids

    results = []
    for name, ids in find_duplicate_device_io(patch_dict).items():
        results.append(CriticResult(
            "warning",
            f"Device has {len(ids)} {name} boxes ({', '.join(ids)}) -- "
            + ("two pass-throughs double the signal into Live"
               if name in ("plugin~", "plugout~")
               else "every dial is initialized twice"),
            f"Keep one {name} and rewire its cords; add_m4l_device reuses an "
            f"existing one",
            rule="duplicate_device_io",
            box_ids=finding_ids(*ids),
        ))
    return results


def _single(patcher, name: str):
    """The one top-level *name* box, None when absent; ValueError when several."""
    found = [b for b in patcher.boxes if b.name == name]
    if len(found) > 1:
        raise ValueError(
            f"the patcher already has {len(found)} {name} boxes "
            f"({', '.join(b.id for b in found)}); a device needs exactly one -- "
            f"remove the duplicate before calling add_m4l_device"
        )
    return found[0] if found else None


def _feeds(patcher, box, inlet: int) -> list:
    """(source id, outlet) of every cord into *box* inlet *inlet*."""
    return [(l.source_id, l.source_outlet) for l in patcher.lines
            if l.dest_id == box.id and l.dest_inlet == inlet]


def _check_free_inlets(patcher, out_box, plan: list, label: str) -> None:
    """Refuse a source cord into an inlet another source already feeds."""
    if out_box is None:
        return
    for inlet, (box, outlet) in plan:
        feeds = _feeds(patcher, out_box, inlet)
        if feeds and feeds != [(box.id, outlet)]:
            others = ", ".join(f"{sid}[{so}]" for sid, so in feeds)
            raise ValueError(
                f"{label}: {out_box.name} ({out_box.id}) inlet {inlet} is already fed "
                f"by {others}; a second source would sum two paths into Live -- "
                f"rewire the existing chain or omit the source"
            )


def _is_bang_trigger(box) -> bool:
    return box.name in _TRIGGER_NAMES and bool(box.args) and all(
        str(a) in ("b", "bang") for a in box.args)


def _rect(box) -> list:
    from src.maxpat.sizing import rendered_rect

    r = rendered_rect(box)
    return list(r) if r is not None else list(box.patching_rect)


def _rects_touch(a: list, b: list, pad: float = 5.0) -> bool:
    half = pad / 2.0
    return not (a[0] + a[2] + half <= b[0] - half or b[0] + b[2] + half <= a[0] - half
                or a[1] + a[3] + half <= b[1] - half or b[1] + b[3] + half <= a[1] - half)


def _clear_of_existing(patcher, before: set) -> None:
    """Move this call's new boxes right of the existing ones on an overlap (IN-06).

    The builder places its boxes at fixed coordinates; when any of them
    overlaps a box that was in the patcher before the call, all new boxes
    shift right together (their relative layout kept) to 30 px past the
    existing boxes' right edge. No overlap -> nothing moves.
    """
    new = [b for b in patcher.boxes if id(b) not in before]
    old = [b for b in patcher.boxes if id(b) in before]
    if not new or not old:
        return
    old_rects = [_rect(b) for b in old]
    if not any(_rects_touch(_rect(n), r) for n in new for r in old_rects):
        return
    right = max(r[0] + r[2] for r in old_rects)
    dx = right + 30.0 - min(float(b.patching_rect[0]) for b in new)
    for b in new:
        b.patching_rect[0] = float(b.patching_rect[0]) + dx


def build_m4l_device(
    patcher,
    kind: str,
    params: "list | None" = None,
    *,
    audio_source=None,
    midi_source=None,
    midi_in: bool = True,
    init_chain: bool = True,
    banks: bool = True,
    presentation: bool = True,
    modmode: "ModMode | int | str" = ModMode.NONE,
    info_text: "bool | None" = None,
) -> M4LDevice:
    """Build the device skeleton into *patcher*. EXPERIMENTAL (Live check pending).

    See ``Patcher.add_m4l_device`` for the full contract. Everything is
    validated before the first box is created. Box creation order is fixed
    -- I/O boxes, I/O cords, dials, then live.thisdevice / trigger and
    live.banks -- so add_m4l_gen_synth's ids hold.

    Existing device content is reused, never doubled (review BL-01):

    - The kind's I/O boxes (``plugin~`` / ``plugout~``, ``midiin`` /
      ``midiout``; an instrument's ``midiin`` when ``midi_in``) and
      ``live.thisdevice`` are looked up by name in the top scope. One that
      exists is reused; two or more of one name -> ValueError (ambiguous).
    - The pass-through (``plugin~`` 0->0 / 1->1, ``midiin -> midiout``) is
      added only into output inlets that nothing feeds yet, so a user chain
      ``plugin~ -> fx -> plugout~`` never gets a dry path beside it.
    - A source cord into an output inlet that another source already feeds
      -> ValueError; the same cord again is a no-op.
    - A reused ``live.thisdevice`` keeps a single cord from outlet 0: with
      no cord the new unbound dials are wired as for a fresh device; one
      cord into an all-bang ``t b ...`` extends that trigger
      (``replace_box_safe``, existing cords kept) with one outlet per new
      dial; any other cord(s) move onto a new ``t b ...`` (existing
      destinations on the left outlets, the new dials on the right).
    - Param names equal to an existing ``parameter_longname``, and explicit
      short names equal to an existing short name, are refused (review
      WR-01); auto short names avoid the existing ones.

    Init chain (``init_chain=True``): ``live.thisdevice`` outlet 0 bangs
    when the device is opened and completely initialized, every time a
    preset is loaded and when the device is saved (refpage
    live.thisdevice.maxref.xml). Every dial WITHOUT ``param_connect`` is
    banged so it re-outputs its restored value to the caller's DSP: one
    unbound dial gets a direct cord, two or more get ``t b b ...`` fired
    right to left. gen~-bound dials are served by ``param_connect`` and get
    no cord. With no unbound dial, live.thisdevice stands alone (it still
    marks the patch as a device for ``detect_m4l_device_type``).
    [ASSUMED] that a banged live.dial re-outputs in Live -- part of the
    Q40 Live check.

    Banks (``banks=True`` and at least one param):
    ``patcher.parameters.parameterbanks`` = ``m4l_polish.plan_push_banks``
    of the longnames, unless user-defined banks are already there (kept,
    with a UserWarning); one newobj ``live.banks`` (an existing one is
    reused).

    Info text (``info_text``; None follows ``presentation``): every new dial
    gets ``annotation`` / ``annotation_name`` exactly as
    ``m4l_polish.populate_info_text`` writes them (review IN-06). The bare
    skeleton (``presentation=False``, as add_m4l_gen_synth builds it) has
    none, so its golden output holds.

    Layout: when a new box overlaps a box that was in the patcher before
    the call, all new boxes move right of the existing ones together
    (review IN-06).
    """
    if kind not in KIND_CODES:
        raise ValueError(f"unknown device kind {kind!r}; expected one of {sorted(KIND_CODES)}")
    specs = resolve_param_specs(
        list(params or []),
        modmode=modmode,
        existing_longnames=_existing_param_longnames(patcher),
        existing_shortnames=_existing_param_names(patcher, "parameter_shortname"),
    )
    audio = _normalize_source(patcher, audio_source, "audio_source", allow_pair=True)
    midi = _normalize_source(patcher, midi_source, "midi_source", allow_pair=False)
    if audio is not None and kind == "midi_effect":
        raise ValueError("audio_source is not valid for a midi_effect (it has no plugout~)")
    if midi is not None and kind != "midi_effect":
        raise ValueError("midi_source is only valid for a midi_effect (midiout)")
    check_varname_collisions(patcher, [s["varname"] for s in specs])

    # Existing device I/O (BL-01): reuse each, refuse ambiguity.
    in_name, out_name = _KIND_IO[kind]
    wants_in = kind != "instrument" or midi_in
    existing_in = _single(patcher, in_name) if wants_in else None
    existing_out = _single(patcher, out_name)
    existing_dev = _single(patcher, "live.thisdevice") if init_chain else None

    # With a source, the caller's chain already holds the device input
    # (plugin~ / midiin): reuse it instead of adding a second, unwired one
    # (review WR-01). The source must exist before the build, so the chain
    # cannot start from a box this call would create.
    if kind == "audio_effect" and audio is not None and existing_in is None:
        raise ValueError(
            "audio_source on an audio_effect needs the chain's plugin~ in the "
            "patcher first (build it from patcher.add_box('plugin~')), or omit "
            "audio_source for the plugin~ -> plugout~ pass-through"
        )
    if kind == "midi_effect" and midi is not None and existing_in is None:
        raise ValueError(
            "midi_source on a midi_effect needs the chain's midiin in the "
            "patcher first (build it from patcher.add_box('midiin')), or omit "
            "midi_source for the midiin -> midiout pass-through"
        )

    # Source cords planned as (output inlet, (box, outlet)).
    if midi is not None:
        source_plan = [(0, midi[0])]
    elif audio is not None:
        source_plan = ([(0, audio[0]), (1, audio[0])] if len(audio) == 1
                       else [(0, audio[0]), (1, audio[1])])
    else:
        source_plan = []
    _check_free_inlets(patcher, existing_out, source_plan,
                       "midi_source" if midi is not None else "audio_source")

    before = {id(b) for b in patcher.boxes}
    dev = M4LDevice(kind=kind)

    # 1. Input box, 2. output box (Live template objects, bare forms).
    if wants_in:
        box = existing_in or patcher.add_box(in_name, x=200.0, y=340.0)
        if in_name == "plugin~":
            dev.plugin = box
        else:
            dev.midiin = box
    out_box = existing_out or patcher.add_box(out_name, x=200.0, y=400.0)
    if out_name == "plugout~":
        dev.plugout = out_box
    else:
        dev.midiout = out_box

    # 3. I/O cords, inlet 0 before inlet 1. The pass-through goes only into
    # inlets nothing feeds yet (a reused output keeps its chain; BL-01).
    if source_plan:
        for inlet, (box, outlet) in source_plan:
            patcher.add_connection(box, outlet, out_box, inlet)
    elif kind == "audio_effect":
        for k in (0, 1):
            if not _feeds(patcher, out_box, k):
                patcher.add_connection(dev.plugin, k, out_box, k)
    elif kind == "midi_effect":
        if not _feeds(patcher, out_box, 0):
            patcher.add_connection(dev.midiin, 0, out_box, 0)

    # 4. Parameter dials.
    if info_text is None:
        info_text = presentation
    if info_text:
        from src.maxpat.m4l_polish import _make_generic_info_text
    for i, spec in enumerate(specs):
        d = patcher.add_box(
            "live.dial", x=50.0 + i * 60.0, y=100.0, skip_overlap_check=True,
        )
        d.extra_attrs["varname"] = spec["varname"]
        if spec["param_connect"] is not None:
            d.extra_attrs["param_connect"] = spec["param_connect"]
        d.extra_attrs["parameter_enable"] = 1
        valueof = {
            "parameter_initial": [spec["default"]],
            "parameter_initial_enable": 1,
            "parameter_longname": spec["name"],
            "parameter_shortname": spec["short_name"],
            "parameter_mmin": spec["min"],
            "parameter_mmax": spec["max"],
            "parameter_modmode": spec["modmode"],
            "parameter_type": spec["type"],
            "parameter_unitstyle": spec["unit"],
        }
        if spec["steps"] is not None:
            valueof["parameter_steps"] = spec["steps"]
        d.extra_attrs["saved_attribute_attributes"] = {"valueof": valueof}
        if info_text:
            d.extra_attrs["annotation"] = _make_generic_info_text(spec["name"], valueof)
            d.extra_attrs["annotation_name"] = spec["name"]
        dev.dials.append(d)

    # 5. live.thisdevice init chain, after the dials (ids of the legacy path hold).
    if init_chain:
        unbound = [d for d, spec in zip(dev.dials, specs) if spec["param_connect"] is None]
        if existing_dev is None:
            dev.thisdevice = patcher.add_box(
                "live.thisdevice", x=50.0, y=20.0, skip_overlap_check=True,
            )
            current = []
        else:
            dev.thisdevice = existing_dev
            current = [l for l in patcher.lines
                       if l.source_id == existing_dev.id and l.source_outlet == 0]
        if unbound:
            _wire_init_chain(patcher, dev, unbound, current)

    # 6. Push parameterbanks + live.banks.
    if banks and dev.dials:
        from src.maxpat.m4l_polish import _banks_replaceable, plan_push_banks

        parameters = patcher.props.setdefault("parameters", {})
        if _banks_replaceable(parameters.get("parameterbanks")):
            # Every device parameter, not only this call's (review WR-04):
            # once written the banks are no longer placeholders, so polish
            # would never add the earlier ones.
            new_names = [s["name"] for s in specs]
            earlier = [n for n in _existing_param_longnames(patcher) if n not in new_names]
            parameters["parameterbanks"] = plan_push_banks(earlier + new_names)
        else:
            warnings.warn(
                "patcher.parameters.parameterbanks already holds user-defined banks "
                "-- kept; the new parameters are not added to them",
                UserWarning,
                stacklevel=3,
            )
        dev.banks = next((b for b in patcher.boxes if b.name == "live.banks"), None)
        if dev.banks is None:
            dev.banks = patcher.add_box(
                "live.banks", x=350.0, y=400.0, skip_overlap_check=True,
            )

    _clear_of_existing(patcher, before)

    # Presentation grid inside Live's 169 px device height (Rule #9).
    # Existing presentation UI is kept: the grid starts right of it and
    # devicewidth only grows; openrect/latency are set only when absent
    # (review WR-03).
    if presentation and dev.dials:
        # Measured before the dials join presentation.
        right, has_ui = _presentation_extent(patcher)
        x0 = right + _GRID_MARGIN if has_ui else _GRID_MARGIN
        ncols = _presentation_cols(len(dev.dials))
        for i, d in enumerate(dev.dials):
            row, col = divmod(i, ncols)
            patcher.add_to_presentation(d, [
                x0 + _GRID_DX * col,
                _GRID_MARGIN + _GRID_DY * row,
                _DIAL_W,
                _DIAL_H,
            ])
        patcher.props["openinpresentation"] = 1
        width = x0 + _GRID_DX * ncols
        current = patcher.props.get("devicewidth")
        if isinstance(current, (int, float)) and current > width:
            width = current
        patcher.props["devicewidth"] = width
        if patcher.props.get("openrect") is None:
            patcher.props["openrect"] = [0.0, 0.0, 0.0, DEVICE_HEIGHT]
        if patcher.props.get("latency") is None:
            patcher.props["latency"] = 0

    return dev


def _wire_init_chain(patcher, dev: M4LDevice, unbound: list, current: list) -> None:
    """Bang *unbound* dials from ``dev.thisdevice`` outlet 0, never fanning out.

    *current* holds the cords already leaving outlet 0 (a reused
    live.thisdevice; BL-01).
    """
    td = dev.thisdevice
    tx, ty = float(td.patching_rect[0]), float(td.patching_rect[1])
    if not current:
        if len(unbound) == 1:
            patcher.add_connection(td, 0, unbound[0], 0)
            return
        dev.init_trigger = patcher.add_box(
            "t", ["b"] * len(unbound), x=tx, y=ty + 40.0, skip_overlap_check=True,
        )
        patcher.add_connection(td, 0, dev.init_trigger, 0)
        for j, dial in enumerate(unbound):
            patcher.add_connection(dev.init_trigger, j, dial, 0)
        return

    by_id = {b.id: b for b in patcher.boxes}
    if len(current) == 1 and current[0].dest_inlet == 0:
        dest = by_id.get(current[0].dest_id)
        if dest is not None and _is_bang_trigger(dest):
            k = dest.numoutlets
            result = patcher.replace_box_safe(dest, "t", args=["b"] * (k + len(unbound)))
            trig = result.box
            for j, dial in enumerate(unbound):
                patcher.add_connection(trig, k + j, dial, 0)
            dev.init_trigger = trig
            return

    # Move the existing destinations onto a new all-bang trigger (left
    # outlets, fired last), the new dials on its right outlets.
    targets = [(by_id[l.dest_id], l.dest_inlet) for l in current if l.dest_id in by_id]
    for l in current:
        patcher.lines.remove(l)
    trig = patcher.add_box(
        "t", ["b"] * (len(targets) + len(unbound)), x=tx, y=ty + 40.0,
        skip_overlap_check=True,
    )
    patcher.add_connection(td, 0, trig, 0)
    for j, (box, inlet) in enumerate(targets):
        patcher.add_connection(trig, j, box, inlet)
    for j, dial in enumerate(unbound):
        patcher.add_connection(trig, len(targets) + j, dial, 0)
    dev.init_trigger = trig
