"""M4L polish -- post-process parameter metadata for M4L devices.

Auto-derives longname, shortname, and varname for M4L live.* controls,
organizes parameters into Push controller banks, and populates info text
annotations for Ableton Info View.

Rules:
  SCAFFOLD-04: ensure_parameter_enable sets parameter_enable=1 + saved_attribute_attributes
               on parameter-capable live.* controls only (LIVE_PARAMETER_OBJECTS);
               Float type/unitstyle defaults only on float-native classes
  SCAFFOLD-05: ensure_m4l_prefixes adds the --- prefix to device-local names
               consistently across every reference, or leaves a name alone
               and reports it (plan_m4l_prefixes; review D2)
  D-01: Never override existing non-empty values
  D-02: Derive longname from varname (snake_case -> Title Case)
  D-03: Derive shortname from longname via abbreviation table (max 8 chars)
  D-04: Derive varname from longname (Title Case -> snake_case)
  D-05: Parameters grouped into banks of 8 by semantic function
  D-06: Bank names auto-derived from parameter group content
  D-07: Partial banks padded with empty slots (dash)
  Banks are stored where MAX keeps them: patcher.parameters.parameterbanks
  D-08: Info text describes what the parameter does
  D-09: Info text includes range from unitstyle and mmin/mmax
  D-10: Existing annotations not overridden
  D-11: polish_m4l_device composes all passes in order
"""

from __future__ import annotations

import re
import warnings

from src.maxpat.critics.m4l_critic import LIVE_PARAMETER_OBJECTS
from src.maxpat.db_lookup import inner_patcher_scope
from src.maxpat.m4l_constants import ParamType, UnitStyle
from src.maxpat.utils import get_box_name

# Parameter-capable live.* classes whose native type is Float, so polish may
# default parameter_type/unitstyle to Float. Bundle help/example patches
# (Max 9.2.0) save live.dial as type 0 in 1447/1657 boxes, live.numbox
# 884/1090, live.slider 34/51 and live.gain~ 444/445. The others are not
# Float-native (live.tab type 2 in 328/328, live.menu 366/369, live.text
# 1608/1624, live.toggle 732/735, live.button 218/268; live.grid/live.step
# type 3), so they keep MAX's class default.
_FLOAT_NATIVE_LIVE_CLASSES = frozenset({
    "live.dial", "live.numbox", "live.slider", "live.gain~",
})


# ---------------------------------------------------------------------------
# Abbreviation table for shortname derivation (D-03)
# ---------------------------------------------------------------------------

_ABBREVIATIONS: dict[str, str] = {
    "frequency": "Freq",
    "resonance": "Reso",
    "envelope": "Env",
    "modulation": "Mod",
    "amplitude": "Amp",
    "oscillator": "Osc",
    "sustain": "Sust",
    "release": "Rel",
    "attack": "Atk",
    "decay": "Dcy",
    "velocity": "Vel",
    "volume": "Vol",
    "feedback": "Fdbk",
    "distortion": "Dist",
    "compressor": "Comp",
    "threshold": "Thresh",
    "milliseconds": "ms",
    "filter": "Filt",
    "output": "Out",
    "input": "In",
    "level": "Lvl",
}


# ---------------------------------------------------------------------------
# Name conversion helpers
# ---------------------------------------------------------------------------

def _varname_to_longname(varname: str) -> str:
    """Convert snake_case varname to Title Case longname.

    "filter_cutoff" -> "Filter Cutoff"
    """
    return varname.replace("_", " ").title()


def _longname_to_varname(longname: str) -> str:
    """Convert Title Case longname to snake_case varname.

    "Filter Cutoff" -> "filter_cutoff"
    """
    return longname.lower().replace(" ", "_")


def _abbreviate_shortname(longname: str, max_len: int = 8) -> str:
    """Abbreviate longname for Push display (max 8 chars).

    Strategy:
    1. If already fits, return as-is
    2. Apply abbreviation table word-by-word
    3. If still too long, drop leading words one at a time
    4. Final hard truncation at max_len
    """
    if len(longname) <= max_len:
        return longname

    # Abbreviate each word
    words = longname.split()
    abbreviated = []
    for word in words:
        lower = word.lower()
        if lower in _ABBREVIATIONS:
            abbreviated.append(_ABBREVIATIONS[lower])
        else:
            abbreviated.append(word)

    result = " ".join(abbreviated)
    if len(result) <= max_len:
        return result

    # Drop leading words until it fits
    while len(abbreviated) > 1 and len(" ".join(abbreviated)) > max_len:
        abbreviated.pop(0)

    result = " ".join(abbreviated)
    if len(result) <= max_len:
        return result

    # Final hard truncation
    return result[:max_len]


# ---------------------------------------------------------------------------
# Live control collection (recursive)
# ---------------------------------------------------------------------------

def _collect_live_controls(boxes: list[dict]) -> list[dict]:
    """Recursively collect all parameter-capable live.* control boxes.

    Returns the inner box dicts (not the wrapper {"box": ...}). Only classes
    in LIVE_PARAMETER_OBJECTS are collected; live.comment, live.line,
    live.meter~, live.thisdevice, live.banks etc. are not parameters.
    """
    controls: list[dict] = []

    for box_entry in boxes:
        box = box_entry.get("box", box_entry)
        maxclass = box.get("maxclass", "")

        # Collect live.* controls that are parameterizable
        if maxclass in LIVE_PARAMETER_OBJECTS:
            controls.append(box)

        # Recurse into subpatchers
        inner_patcher = box.get("patcher")
        if inner_patcher:
            inner_boxes = inner_patcher.get("boxes", [])
            controls.extend(_collect_live_controls(inner_boxes))

    return controls


# ---------------------------------------------------------------------------
# SCAFFOLD-04: Parameter enable enforcement
# ---------------------------------------------------------------------------

def ensure_parameter_enable(patch_dict: dict) -> dict:
    """Set parameter_enable=1 and saved_attribute_attributes on live.* controls.

    Fills gaps only -- never overrides existing values (D-05).
    Only parameter-capable classes (LIVE_PARAMETER_OBJECTS) are touched.
    parameter_type / parameter_unitstyle default to Float only on the
    float-native classes (_FLOAT_NATIVE_LIVE_CLASSES); other controls get an
    empty valueof dict so MAX's class default type applies.

    Must run BEFORE derive_parameter_names() so the valueof dict exists
    when the naming pass fills in parameter_longname.
    """
    patcher = patch_dict.get("patcher", {})
    boxes = patcher.get("boxes", [])
    controls = _collect_live_controls(boxes)

    for box in controls:
        if not box.get("parameter_enable"):
            box["parameter_enable"] = 1

        saa = box.setdefault("saved_attribute_attributes", {})
        valueof = saa.setdefault("valueof", {})
        if box.get("maxclass") in _FLOAT_NATIVE_LIVE_CLASSES:
            valueof.setdefault("parameter_type", int(ParamType.FLOAT))
            valueof.setdefault("parameter_unitstyle", int(UnitStyle.FLOAT))

    return patch_dict


# ---------------------------------------------------------------------------
# SCAFFOLD-05: M4L --- prefix enforcement
# ---------------------------------------------------------------------------

# Declarers: max-scope newobj boxes whose tokens[1] is a device-local name
# that gets the --- prefix. Lone receive names are treated as device-local
# too (as before); a name meant to cross devices must be left out of polish
# or it will be prefixed.
_DECLARER_CLASSES = frozenset({
    "send", "s", "receive", "r", "send~", "receive~",
    "value", "v", "pv", "coll", "dict", "buffer~",
})

# Buffer users whose tokens[1] names a buffer~ (rewritten with it).
_BUFFER_USER_CLASSES = frozenset({
    "play~", "groove~", "index~", "peek~", "poke~", "info~",
})

# Objects whose code or patcher lives outside the dict (cannot be scanned).
_EXTERNAL_CLASSES = frozenset({
    "js", "jsui", "v8", "v8ui", "node.script", "poly~", "mc.poly~",
    "pfft~", "bpatcher",
})
_EXTERNAL_MAXCLASSES = frozenset({"jsui", "v8ui", "bpatcher"})

# Subpatcher title tokens are labels, not name references.
_TITLE_CLASSES = frozenset({"p", "patcher"})

# Box attributes that never hold a name reference.
_IGNORED_ATTR_KEYS = frozenset({
    "id", "maxclass", "varname", "text", "code", "fontname", "fontface",
    "annotation", "annotation_name", "hint", "comment",
})

_SKIPPED_MAXCLASSES = frozenset({"comment", "live.comment"})
_MESSAGE_SPLIT = re.compile(r"([,;])")
_PREFIX = "---"


def _walk_patch_boxes(boxes: list, scope: str = "max"):
    """Yield (box, scope) for every box, recursing into embedded patchers.

    Comments (comment / live.comment) are skipped entirely.
    """
    for entry in boxes or []:
        if not isinstance(entry, dict):
            continue
        box = entry.get("box", entry)
        if not isinstance(box, dict):
            continue
        if box.get("maxclass") in _SKIPPED_MAXCLASSES:
            continue
        yield box, scope
        inner = box.get("patcher")
        if isinstance(inner, dict):
            yield from _walk_patch_boxes(
                inner.get("boxes", []), inner_patcher_scope(box, scope))


def _tokens(box: dict) -> list[str]:
    text = box.get("text")
    return text.split() if isinstance(text, str) else []


def _is_float(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def _candidate_name(token: str) -> bool:
    return not (token.startswith(("#", "$", "@", _PREFIX)) or _is_float(token))


def _message_segments(text: str) -> list[str]:
    """Split message text on , and ; keeping the separators."""
    return _MESSAGE_SPLIT.split(text)


def _set_target(segment: str) -> str | None:
    """The name of a ``set <name>`` message segment, else None."""
    toks = segment.split()
    if len(toks) >= 2 and toks[0] == "set":
        return toks[1]
    return None


def _describe(box: dict) -> str:
    text = box.get("text")
    label = f"'{text}'" if isinstance(text, str) and text else box.get("maxclass", "?")
    return f"{box.get('id', '?')} {label}"


def plan_m4l_prefixes(patch_dict: dict, db=None) -> dict:
    """Decide which device-local names can be --- prefixed consistently.

    Pure: never mutates patch_dict. Returns
    ``{"rename": [sorted names], "report_only": {name: reason}}``.

    Rules (review D2, Q15):
      - Candidates are tokens[1] of max-scope newobj declarers
        (send/s/receive/r/send~/receive~/value/v/pv/coll/dict/buffer~) that
        are not #/$/@/--- prefixed and not numbers. Names inside gen~/rnbo~
        patchers are never candidates.
      - Positions the pass can rewrite (max scope only): tokens[1] of
        declarers and buffer users (play~/groove~/index~/peek~/poke~/info~),
        waveform~ ``buffername``, and the target of ``set <name>`` message
        segments.
      - A candidate is report-only when the name also appears anywhere else
        (any scope): as another newobj token (p/patcher titles excepted), a
        message token (e.g. ``; level 0.5``), a delimited word in a box's
        ``code``, or a top-level string attribute of another box (e.g. umenu
        items); when it is used by a buffer user / waveform~ with no local
        ``buffer~ <name>``; when ``---<name>`` already exists; or when the
        patch holds external code or patchers (js, jsui, v8, v8ui,
        node.script, poly~, mc.poly~, pfft~, non-embedded bpatcher, or an
        abstraction unknown to the object DB), which cannot be scanned.
      - Comments are never read or written.
    """
    patcher = patch_dict.get("patcher", {}) if isinstance(patch_dict, dict) else {}
    walked = list(_walk_patch_boxes(patcher.get("boxes", [])))

    candidates: set[str] = set()
    buffer_declared: set[str] = set()
    for box, scope in walked:
        if scope != "max" or box.get("maxclass") != "newobj":
            continue
        toks = _tokens(box)
        if len(toks) >= 2 and toks[0] in _DECLARER_CLASSES and _candidate_name(toks[1]):
            candidates.add(toks[1])
            if toks[0] == "buffer~":
                buffer_declared.add(toks[1])

    report: dict[str, str] = {}

    def block(name: str, reason: str) -> None:
        if name in candidates and name not in report:
            report[name] = reason

    if not candidates:
        return {"rename": [], "report_only": {}}

    # External code / patchers: nothing can be proven safe.
    external = None
    for box, scope in walked:
        if scope != "max" or isinstance(box.get("patcher"), dict):
            continue
        maxclass = box.get("maxclass", "")
        if maxclass in _EXTERNAL_MAXCLASSES:
            external = box
            break
        if maxclass == "newobj":
            toks = _tokens(box)
            if not toks:
                continue
            if toks[0] in _EXTERNAL_CLASSES:
                external = box
                break
            if db is None:
                from src.maxpat.db_lookup import ObjectDatabase
                db = ObjectDatabase()
            if not db.exists(toks[0]):
                external = box
                break
    if external is not None:
        reason = f"external code/patcher {_describe(external)} cannot be scanned"
        for name in sorted(candidates):
            block(name, reason)

    prefixed_present: set[str] = set()
    for box, scope in walked:
        maxclass = box.get("maxclass", "")
        toks = _tokens(box)
        if maxclass == "newobj":
            if toks and toks[0] in _TITLE_CLASSES:
                continue
            handled = (scope == "max" and len(toks) >= 2
                       and (toks[0] in _DECLARER_CLASSES
                            or toks[0] in _BUFFER_USER_CLASSES))
            for i, tok in enumerate(toks):
                if tok.startswith(_PREFIX):
                    prefixed_present.add(tok[len(_PREFIX):])
                if handled and i == 1:
                    continue
                block(tok, f"newobj {_describe(box)} references it")
            if (scope == "max" and len(toks) >= 2
                    and toks[0] in _BUFFER_USER_CLASSES
                    and toks[1] not in buffer_declared):
                block(toks[1], f"{_describe(box)} uses it with no local buffer~")
        elif maxclass == "message":
            text = box.get("text") if isinstance(box.get("text"), str) else ""
            for seg in _message_segments(text):
                if seg in (",", ";"):
                    continue
                target = _set_target(seg) if scope == "max" else None
                for i, tok in enumerate(seg.split()):
                    tok = tok.rstrip(",;")
                    if tok.startswith(_PREFIX):
                        prefixed_present.add(tok[len(_PREFIX):])
                    if target is not None and i == 1:
                        continue
                    block(tok, f"message {_describe(box)} references it")
        else:
            for key, value in box.items():
                if key in _IGNORED_ATTR_KEYS:
                    continue
                values = value if isinstance(value, list) else [value]
                for v in values:
                    if not isinstance(v, str):
                        continue
                    if v.startswith(_PREFIX):
                        prefixed_present.add(v[len(_PREFIX):])
                    if (key == "buffername" and maxclass == "waveform~"
                            and scope == "max"):
                        if v not in buffer_declared:
                            block(v, f"{_describe(box)} uses it with no local buffer~")
                        continue
                    block(v, f"{_describe(box)} attribute '{key}' references it")
        code = box.get("code")
        if isinstance(code, str):
            for name in candidates:
                if re.search(r"(?<![\w.~\-])" + re.escape(name) + r"(?![\w.~\-])", code):
                    block(name, f"code in {_describe(box)} references it")

    for name in sorted(candidates & prefixed_present):
        block(name, f"{_PREFIX}{name} already exists; renaming would merge them")

    return {
        "rename": sorted(candidates - set(report)),
        "report_only": {name: report[name] for name in sorted(report)},
    }


def ensure_m4l_prefixes(patch_dict: dict, db=None) -> dict:
    """Add the --- prefix to device-local names, consistently or not at all.

    Uses plan_m4l_prefixes: each name in ``rename`` is rewritten at every
    handled max-scope position (declarer / buffer-user tokens[1], waveform~
    buffername, ``set <name>`` message targets), so senders, receivers and
    buffer users stay linked. Names in ``report_only`` are left untouched and
    reported in one UserWarning. Comments are never touched. Idempotent.
    """
    plan = plan_m4l_prefixes(patch_dict, db=db)
    rename = set(plan["rename"])
    if rename:
        patcher = patch_dict.get("patcher", {})
        for box, scope in list(_walk_patch_boxes(patcher.get("boxes", []))):
            if scope != "max":
                continue
            _rename_in_box(box, rename)
    if plan["report_only"]:
        details = "; ".join(f"{n} ({r})" for n, r in plan["report_only"].items())
        warnings.warn(
            f"ensure_m4l_prefixes: left {len(plan['report_only'])} name(s) "
            f"unprefixed: {details}",
            UserWarning,
            stacklevel=2,
        )
    return patch_dict


def _rename_in_box(box: dict, rename: set) -> None:
    """Rewrite the handled positions of one max-scope box."""
    maxclass = box.get("maxclass", "")
    if maxclass == "newobj":
        toks = _tokens(box)
        if (len(toks) >= 2 and toks[1] in rename
                and (toks[0] in _DECLARER_CLASSES
                     or toks[0] in _BUFFER_USER_CLASSES)):
            toks[1] = _PREFIX + toks[1]
            box["text"] = " ".join(toks)
    elif maxclass == "message":
        text = box.get("text")
        if not isinstance(text, str):
            return
        parts = _message_segments(text)
        changed = False
        for i, seg in enumerate(parts):
            if seg in (",", ";"):
                continue
            target = _set_target(seg)
            if target is not None and target in rename:
                parts[i] = re.sub(
                    r"^(\s*set\s+)" + re.escape(target) + r"(?=\s|$)",
                    lambda m: m.group(1) + _PREFIX + target,
                    seg,
                )
                changed = True
        if changed:
            box["text"] = "".join(parts)
    elif maxclass == "waveform~":
        name = box.get("buffername")
        if isinstance(name, str) and name in rename:
            box["buffername"] = _PREFIX + name


# ---------------------------------------------------------------------------
# POLISH-01: Parameter name derivation
# ---------------------------------------------------------------------------

def derive_parameter_names(patch_dict: dict) -> dict:
    """Auto-derive longname/shortname/varname for all live.* controls.

    Mutates patch_dict in place. Returns the same dict.

    Rules:
      - Never override existing non-empty values (D-01)
      - Derive longname from varname or box text (D-02)
      - Derive shortname from longname via abbreviation (D-03)
      - Derive varname from longname (D-04)
      - Resolve duplicate longnames with index suffix
    """
    patcher = patch_dict.get("patcher", {})
    boxes = patcher.get("boxes", [])
    controls = _collect_live_controls(boxes)

    # Phase 1: Derive names for each control
    for box in controls:
        # Ensure saved_attribute_attributes.valueof exists
        saa = box.setdefault("saved_attribute_attributes", {})
        valueof = saa.setdefault("valueof", {})

        existing_longname = valueof.get("parameter_longname", "")
        existing_shortname = valueof.get("parameter_shortname", "")
        existing_varname = box.get("varname", "")

        # D-02: Derive longname if missing
        if not existing_longname:
            if existing_varname:
                valueof["parameter_longname"] = _varname_to_longname(existing_varname)
            else:
                # Try deriving from box text (e.g., "live.dial pitch_start")
                text = box.get("text", "")
                if text:
                    tokens = text.split()
                    # Skip the maxclass token (first word)
                    if len(tokens) > 1:
                        varname_from_text = tokens[1]
                        valueof["parameter_longname"] = _varname_to_longname(varname_from_text)

        # D-04: Derive varname if missing (needs longname to exist now)
        current_longname = valueof.get("parameter_longname", "")
        if not existing_varname and current_longname:
            box["varname"] = _longname_to_varname(current_longname)

        # D-03: Derive shortname if missing (needs longname)
        if not existing_shortname and current_longname:
            valueof["parameter_shortname"] = _abbreviate_shortname(current_longname)

    # Phase 2: Resolve duplicate longnames
    _resolve_duplicate_longnames(controls)

    return patch_dict


# ---------------------------------------------------------------------------
# Push bank organization (POLISH-02)
# ---------------------------------------------------------------------------

_BANK_KEYWORDS: dict[str, set[str]] = {
    "Pitch": {"pitch", "tune", "tuning", "detune", "transpose", "semitone", "cent", "octave"},
    "Amp": {"amp", "amplitude", "volume", "level", "gain", "velocity", "body"},
    "Filter": {"filter", "cutoff", "resonance", "reso", "freq", "tone", "drive", "hp", "lp", "bp"},
    "Envelope": {"envelope", "env", "attack", "decay", "sustain", "release", "adsr", "curve"},
    "Mod": {"modulation", "mod", "lfo", "rate", "depth", "amount", "speed"},
    "FX": {"delay", "reverb", "chorus", "flanger", "phaser", "distortion", "comp", "eq"},
    "Noise": {"noise", "sub"},
    "Mix": {"mix", "dry", "wet", "send", "return", "pan", "width"},
}


def _classify_parameter(longname_or_varname: str) -> str:
    """Classify a parameter into a semantic group by keywords.

    Splits on spaces and underscores, scores against _BANK_KEYWORDS.
    First word (prefix) gets +2 bonus if found in any keyword set.
    Returns group name with highest score, or "Main" if no match.
    """
    parts = set(longname_or_varname.lower().replace("_", " ").split())
    # Prefix is the first word
    tokens = longname_or_varname.lower().replace("_", " ").split()
    prefix = tokens[0] if tokens else ""

    best_group = "Main"
    best_score = 0
    for group_name, keywords in _BANK_KEYWORDS.items():
        score = len(parts & keywords)
        # Bonus for prefix match
        if prefix in keywords:
            score += 2
        if score > best_score:
            best_score = score
            best_group = group_name

    return best_group


def plan_push_banks(longnames: list[str]) -> dict:
    """Plan Push parameter banks for *longnames* (pure; no patch mutation).

    Shared by :func:`organize_push_banks` (polish) and the Q40 device builder
    (``m4l_device.build_m4l_device``), so both write the same banks:

    - classify each name with :func:`_classify_parameter`;
    - group in first-appearance order of the groups;
    - chunk each group into banks of 8, padding the last with ``"-"``;
    - name banks "Group", "Group 2", ...

    Returns:
        MAX's saved shape ``{"0": {"index": 0, "name": ..., "parameters":
        [8 longnames / "-"]}, ...}``, or ``{}`` for no names.
    """
    groups: dict[str, list[str]] = {}
    for longname in longnames:
        group = _classify_parameter(longname)
        groups.setdefault(group, []).append(longname)

    # Build bank dicts: chunk each group into banks of 8
    bank_dicts: list[dict] = []
    for group_name, names in groups.items():
        for chunk_idx in range(0, len(names), 8):
            chunk = names[chunk_idx : chunk_idx + 8]
            # Pad to 8
            padded = chunk + ["-"] * (8 - len(chunk))
            # Name: "Filter", "Filter 2", etc.
            bank_num = chunk_idx // 8
            name = group_name if bank_num == 0 else f"{group_name} {bank_num + 1}"
            bank_dicts.append({"name": name, "parameters": padded})

    return {
        str(i): {"index": i, "name": bank["name"],
                 "parameters": bank["parameters"]}
        for i, bank in enumerate(bank_dicts)
    }


def organize_push_banks(patch_dict: dict) -> dict:
    """Organize parameters into semantic Push banks of 8.

    Mutates patch_dict in place. Returns the same dict.

    - Collects all live.* controls via _collect_live_controls
    - Classifies each parameter into a semantic group and chunks each group
      into banks of 8, padding partial banks with "-" (plan_push_banks,
      shared with the Q40 device builder)
    - Writes patcher.parameters.parameterbanks in MAX's saved shape,
      {"0": {"index": 0, "name": ..., "parameters": [8 longnames / "-"]}, ...},
      only when it is absent or all-placeholder (every slot "-", MAX's
      default); user-defined banks and sibling keys under
      patcher.parameters are left untouched (D-01)
    - Creates or reuses the live.banks box (either form); a new one is a
      newobj with text "live.banks", as MAX saves it. A stale private
      _parameter_banks key on an existing box is removed.
    """
    patcher = patch_dict.get("patcher", {})
    boxes = patcher.get("boxes", [])
    controls = _collect_live_controls(boxes)

    if not controls:
        return patch_dict

    # Collect longnames in box order
    longnames: list[str] = []
    for box in controls:
        saa = box.get("saved_attribute_attributes", {})
        valueof = saa.get("valueof", {})
        longname = valueof.get("parameter_longname", "")
        if not longname:
            continue
        longnames.append(longname)

    if not longnames:
        return patch_dict

    parameterbanks = plan_push_banks(longnames)
    parameters = patcher.setdefault("parameters", {})
    if _banks_replaceable(parameters.get("parameterbanks")):
        parameters["parameterbanks"] = parameterbanks

    # Find or create live.banks box (newobj text or legacy maxclass form)
    banks_box = None
    for entry in boxes:
        box = entry.get("box", entry)
        if get_box_name(box) == "live.banks":
            banks_box = box
            break

    if banks_box is None:
        # help/m4l/live.banks.maxhelp saves live.banks as a newobj; a
        # maxclass "live.banks" box is refused by validate_patch.
        banks_box = {
            "id": "obj-live-banks",
            "maxclass": "newobj",
            "text": "live.banks",
            "numinlets": 1,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [20.0, 20.0, 315.0, 45.0],
        }
        boxes.append({"box": banks_box})

    banks_box.pop("_parameter_banks", None)

    return patch_dict


def _banks_replaceable(existing) -> bool:
    """True when parameterbanks is absent or MAX's all-"-" placeholder."""
    if not existing:
        return True
    if not isinstance(existing, dict):
        return False
    for bank in existing.values():
        if not isinstance(bank, dict):
            return False
        if any(slot != "-" for slot in bank.get("parameters", [])):
            return False
    return True


def _resolve_duplicate_longnames(controls: list[dict]) -> None:
    """Append index suffix to duplicate longnames."""
    # Collect all longnames with their box refs
    longname_groups: dict[str, list[dict]] = {}
    for box in controls:
        saa = box.get("saved_attribute_attributes", {})
        valueof = saa.get("valueof", {})
        ln = valueof.get("parameter_longname", "")
        if ln:
            longname_groups.setdefault(ln, []).append(valueof)

    # For any group with duplicates, rename later occurrences
    for longname, valueofs in longname_groups.items():
        if len(valueofs) <= 1:
            continue
        # First occurrence keeps the name, subsequent get " 2", " 3", etc.
        for i, valueof in enumerate(valueofs[1:], start=2):
            valueof["parameter_longname"] = f"{longname} {i}"


# ---------------------------------------------------------------------------
# Info text / annotations (POLISH-03)
# ---------------------------------------------------------------------------

_UNIT_LABELS: dict[int, str] = {
    UnitStyle.INT: "",
    UnitStyle.FLOAT: "",
    UnitStyle.TIME: "ms",
    UnitStyle.HERTZ: "Hz",
    UnitStyle.DECIBEL: "dB",
    UnitStyle.PERCENT: "%",
    UnitStyle.PAN: "(L/R)",
    UnitStyle.SEMITONES: "st",
    UnitStyle.MIDI: "(MIDI)",
    UnitStyle.CUSTOM: "",
}


def _make_range_text(valueof: dict) -> str:
    """Build range string from parameter metadata (D-09).

    Returns empty string if mmin and mmax are both absent.
    Uses :g format to strip trailing zeros (20.0 -> "20").
    """
    mmin = valueof.get("parameter_mmin")
    mmax = valueof.get("parameter_mmax")
    unitstyle = valueof.get("parameter_unitstyle", 0)

    if mmin is None and mmax is None:
        return ""

    label = _UNIT_LABELS.get(unitstyle, "")
    parts = []
    if mmin is not None:
        parts.append(f"{mmin:g}")
    if mmax is not None:
        parts.append(f"{mmax:g}")

    range_str = "-".join(parts)
    if label:
        return f"Range: {range_str} {label}"
    return f"Range: {range_str}"


def _make_generic_info_text(longname: str, valueof: dict) -> str:
    """Build generic info text from parameter metadata (D-08).

    Constructs "{longname} control." as base, appends range if available.
    Example: "Filter Cutoff control. Range: 20-20000 Hz"
    """
    text = f"{longname} control."
    range_text = _make_range_text(valueof)
    if range_text:
        text = f"{text} {range_text}"
    return text


def populate_info_text(patch_dict: dict) -> dict:
    """Set annotation and annotation_name on live.* controls.

    Mutates patch_dict in place. Returns the same dict.

    - annotation_name: set to parameter longname (header in Info View)
    - annotation: descriptive text with range info (body in Info View)
    - Both are TOP-LEVEL box attributes (not inside saved_attribute_attributes)
    - Never overrides existing non-empty values (D-10)
    """
    patcher = patch_dict.get("patcher", {})
    boxes = patcher.get("boxes", [])
    controls = _collect_live_controls(boxes)

    for box in controls:
        saa = box.get("saved_attribute_attributes", {})
        valueof = saa.get("valueof", {})
        longname = valueof.get("parameter_longname", "")
        if not longname:
            continue

        # D-10: Only set if not already present
        if not box.get("annotation"):
            box["annotation"] = _make_generic_info_text(longname, valueof)

        if not box.get("annotation_name"):
            box["annotation_name"] = longname

    return patch_dict


# ---------------------------------------------------------------------------
# Top-level compositor (D-11)
# ---------------------------------------------------------------------------

def polish_m4l_device(patch_dict: dict) -> dict:
    """Apply full M4L polish pipeline to a device patch.

    Composes all five polish passes in correct order:
    1. ensure_parameter_enable -- sets parameter_enable=1 + saa defaults (SCAFFOLD-04)
    2. ensure_m4l_prefixes -- --- prefixes names consistently; warns on names it
       cannot rename safely (SCAFFOLD-05)
    3. derive_parameter_names -- fills longname/shortname/varname gaps
    4. organize_push_banks -- groups params into semantic Push banks
    5. populate_info_text -- sets annotation/annotation_name

    Enforcement MUST run before naming (naming needs valueof dict).
    Naming MUST run before banks (banks reference longnames).
    Called explicitly by agents after build, before export (D-12).

    Mutates patch_dict in place. Returns the same dict.
    """
    ensure_parameter_enable(patch_dict)
    ensure_m4l_prefixes(patch_dict)
    derive_parameter_names(patch_dict)
    organize_push_banks(patch_dict)
    populate_info_text(patch_dict)
    return patch_dict
