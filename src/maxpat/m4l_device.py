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
  :class:`M4LDevice`, :func:`build_m4l_device`.

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
    """
    code = _code_for(kind_or_code)
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
            detectable; ``patcher.project.amxdtype`` disagrees with the kind.
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

    if kind is None:
        from src.maxpat.critics.m4l_critic import detect_m4l_device_type

        kind = detect_m4l_device_type(patch)
        if kind is None:
            raise ValueError(
                "cannot detect the device kind (no plugin~, plugout~ or "
                "live.thisdevice); pass kind= explicitly"
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


def unique_shortnames(longnames: list[str], explicit: list) -> list[str]:
    """Short names: explicit ones verbatim, auto ones abbreviated and de-duplicated.

    An auto name is ``m4l_polish._abbreviate_shortname(name, 8)``; when that
    is already taken (by an explicit name or an earlier auto name) it is
    trimmed and suffixed 2, 3, ... within 8 characters ("Amount",
    "Amount2"). Explicit names are never altered and never reused by an auto
    name.
    """
    from src.maxpat.m4l_polish import _abbreviate_shortname

    if len(longnames) != len(explicit):
        raise ValueError("longnames and explicit must have the same length")
    taken = {s for s in explicit if s}
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


def resolve_param_specs(params: list, *, modmode: "ModMode | int | str" = ModMode.NONE) -> list[dict]:
    """Validate parameter spec dicts and resolve inferred metadata.

    Each spec: required ``name``, ``min``, ``max``, ``default``; optional
    ``unit``, ``type``, ``steps``, ``short_name``, ``varname``,
    ``param_connect``, ``modmode``. Explicit keys always win over inference
    (:func:`infer_type_unit`); short names come from
    :func:`unique_shortnames`; ``varname`` defaults to the name when it is a
    valid identifier, else its lowercased ``\\W+`` -> ``_`` form.

    Returns:
        One dict per spec with keys name, min, max, default (as given),
        type, unit, modmode (ints), steps (int or None), short_name,
        varname, param_connect (str or None).

    Raises:
        ValueError: non-dict spec, unknown or missing keys, empty name,
            duplicate names or varnames, non-numeric or bool bounds,
            min >= max, default outside [min, max], steps < 2, an Enum/Blob
            type or a Custom unit.
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

    for key, label in (("name", "name"), ("varname", "varname")):
        seen: set = set()
        for r in resolved:
            if r[key] in seen:
                raise ValueError(f"duplicate parameter {label} {r[key]!r}")
            seen.add(r[key])

    shorts = unique_shortnames([r["name"] for r in resolved], [r["short_name"] for r in resolved])
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


def build_m4l_device(
    patcher,
    kind: str,
    params: "list | None" = None,
    *,
    audio_source=None,
    midi_source=None,
    midi_in: bool = True,
    presentation: bool = True,
    modmode: "ModMode | int | str" = ModMode.NONE,
) -> M4LDevice:
    """Build the device skeleton into *patcher*. EXPERIMENTAL (Live check pending).

    See ``Patcher.add_m4l_device`` for the full contract. Everything is
    validated before the first box is created. Box creation order is fixed
    (I/O boxes, I/O cords, dials, ...) so add_m4l_gen_synth's ids hold.
    """
    if kind not in KIND_CODES:
        raise ValueError(f"unknown device kind {kind!r}; expected one of {sorted(KIND_CODES)}")
    specs = resolve_param_specs(list(params or []), modmode=modmode)
    audio = _normalize_source(patcher, audio_source, "audio_source", allow_pair=True)
    midi = _normalize_source(patcher, midi_source, "midi_source", allow_pair=False)
    if audio is not None and kind == "midi_effect":
        raise ValueError("audio_source is not valid for a midi_effect (it has no plugout~)")
    if midi is not None and kind != "midi_effect":
        raise ValueError("midi_source is only valid for a midi_effect (midiout)")

    dev = M4LDevice(kind=kind)

    # 1. Input box, 2. output box (Live template objects, bare forms).
    if kind == "audio_effect":
        dev.plugin = patcher.add_box("plugin~", x=200.0, y=340.0)
    elif kind == "midi_effect" or midi_in:
        dev.midiin = patcher.add_box("midiin", x=200.0, y=340.0)
    if kind == "midi_effect":
        dev.midiout = patcher.add_box("midiout", x=200.0, y=400.0)
    else:
        dev.plugout = patcher.add_box("plugout~", x=200.0, y=400.0)

    # 3. I/O cords, inlet 0 before inlet 1.
    if kind == "midi_effect":
        if midi is not None:
            box, outlet = midi[0]
            patcher.add_connection(box, outlet, dev.midiout, 0)
        else:
            patcher.add_connection(dev.midiin, 0, dev.midiout, 0)
    elif audio is not None:
        if len(audio) == 1:
            box, outlet = audio[0]
            patcher.add_connection(box, outlet, dev.plugout, 0)
            patcher.add_connection(box, outlet, dev.plugout, 1)
        else:
            (lbox, lout), (rbox, rout) = audio
            patcher.add_connection(lbox, lout, dev.plugout, 0)
            patcher.add_connection(rbox, rout, dev.plugout, 1)
    elif kind == "audio_effect":
        patcher.add_connection(dev.plugin, 0, dev.plugout, 0)
        patcher.add_connection(dev.plugin, 1, dev.plugout, 1)

    # 4. Parameter dials.
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
        dev.dials.append(d)

    # Presentation grid inside Live's 169 px device height (Rule #9).
    if presentation and dev.dials:
        ncols = _presentation_cols(len(dev.dials))
        for i, d in enumerate(dev.dials):
            row, col = divmod(i, ncols)
            patcher.add_to_presentation(d, [
                _GRID_MARGIN + _GRID_DX * col,
                _GRID_MARGIN + _GRID_DY * row,
                _DIAL_W,
                _DIAL_H,
            ])
        patcher.props["openinpresentation"] = 1
        patcher.props["devicewidth"] = _GRID_MARGIN + _GRID_DX * ncols
        patcher.props["openrect"] = [0.0, 0.0, 0.0, DEVICE_HEIGHT]
        patcher.props["latency"] = 0

    return dev
