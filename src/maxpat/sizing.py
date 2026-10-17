"""Content-aware box sizing for MAX objects.

Computes (width, height) for any MAX object box:
- UI objects with fixed dimensions return their standard sizes.
- Objects with audit-based width data return measured widths from help patches.
- Text-based objects (newobj, comment, message) compute width from text length.

Values sourced from 02-RESEARCH.md Example 1, audit data, and MAX 9 default behavior.
"""

import json
import math
import re
from pathlib import Path
from typing import Any

from src.maxpat.defaults import (
    CHAR_WIDTH,
    COMMENT_BASE_HEIGHT,
    COMMENT_CHAR_WIDTH,
    COMMENT_LINE_HEIGHT,
    COMMENT_TEXT_PAD,
    COMMENT_WRAP_RATIO,
    DEFAULT_HEIGHT,
    DEFAULT_PATCHER_PROPS,
    FONT_SIZE,
    MESSAGE_CHAR_WIDTH,
    MESSAGE_CHROME,
    MIN_BOX_WIDTH,
    PADDING,
)


def _load_width_overrides() -> dict[str, dict[str, float]]:
    """Load width override table from audit data.

    Returns dict keyed by object_name, values are dicts with
    arg_count string keys ("0", "1", "default") mapping to widths.
    """
    override_path = Path(__file__).parent.parent.parent / ".claude" / "max-objects" / "audit" / "width-overrides.json"
    if not override_path.exists():
        return {}
    with open(override_path) as f:
        return json.load(f)


_WIDTH_OVERRIDES: dict[str, dict[str, float]] = _load_width_overrides()


def _load_bpatcher_dims() -> dict[str, tuple[float, float]]:
    """Load bpatcher dimensions from package DB entries.

    Scans .claude/max-objects/packages/*/objects.json at import time and
    builds a dict mapping object name to (width, height) for any entry
    with a ``bpatcher_dimensions`` field.
    """
    dims: dict[str, tuple[float, float]] = {}
    pkg_root = Path(__file__).parent.parent.parent / ".claude" / "max-objects" / "packages"
    if not pkg_root.is_dir():
        return dims
    for pkg_dir in pkg_root.iterdir():
        if not pkg_dir.is_dir():
            continue
        json_path = pkg_dir / "objects.json"
        if not json_path.exists():
            continue
        with open(json_path) as f:
            data = json.load(f)
        for name, obj in data.items():
            bp_dims = obj.get("bpatcher_dimensions")
            if bp_dims and len(bp_dims) >= 2:
                dims[name] = (float(bp_dims[0]), float(bp_dims[1]))
    return dims


_BPATCHER_DIMS: dict[str, tuple[float, float]] = _load_bpatcher_dims()


def get_bpatcher_dims(object_name: str) -> tuple[float, float] | None:
    """Return (width, height) for a known bpatcher object, or None."""
    return _BPATCHER_DIMS.get(object_name)


# Fixed sizes for UI objects: maxclass -> (width, height).
# None means the object uses text-based sizing (comment, message).
UI_SIZES: dict[str, tuple[float, float] | None] = {
    "toggle":        (24.0, 24.0),
    "button":        (24.0, 24.0),
    "slider":        (20.0, 140.0),
    "dial":          (40.0, 40.0),
    "number":        (50.0, 22.0),
    "flonum":        (50.0, 22.0),
    "led":           (24.0, 24.0),
    "rslider":       (20.0, 140.0),
    # Labeled parameter banks override this height with 24 px per bar
    # (Patcher.add_labeled_param_bank; CLAUDE.md Rule #4 subsection)
    "multislider":   (200.0, 100.0),
    "kslider":       (336.0, 53.0),
    "nslider":       (40.0, 140.0),
    "panel":         (128.0, 128.0),
    "radiogroup":    (18.0, 82.0),
    "textbutton":    (100.0, 20.0),
    "tab":           (200.0, 24.0),
    "pictctrl":      (100.0, 100.0),
    "pictslider":    (100.0, 100.0),
    "incdec":        (20.0, 24.0),
    "swatch":        (128.0, 64.0),
    "colorpicker":   (221.0, 191.0),
    "chooser":       (100.0, 100.0),
    "listbox":       (100.0, 100.0),
    "umenu":         (100.0, 22.0),
    "textedit":      (200.0, 100.0),
    "attrui":        (150.0, 22.0),
    "preset":        (100.0, 40.0),
    "matrixctrl":    (130.0, 66.0),
    "nodes":         (200.0, 200.0),
    "jsui":          (100.0, 100.0),
    "fpic":          (100.0, 100.0),
    "lcd":           (128.0, 128.0),
    "hint":          (100.0, 22.0),
    "dropfile":      (100.0, 100.0),
    "ubutton":       (100.0, 100.0),
    "playbar":       (320.0, 24.0),
    # Patcher structure
    "inlet":         (30.0, 30.0),
    "outlet":        (30.0, 30.0),
    "bpatcher":      (200.0, 100.0),
    # MSP UI
    "meter~":        (15.0, 100.0),
    "levelmeter~":   (24.0, 128.0),
    "spectroscope~": (300.0, 100.0),
    "scope~":        (130.0, 130.0),
    "number~":       (56.0, 22.0),
    "gain~":         (22.0, 140.0),
    "ezdac~":        (45.0, 45.0),
    "ezadc~":        (45.0, 45.0),
    # Gen~
    "gen~":          (150.0, 22.0),
    # Max for Live UI
    "live.dial":     (44.0, 66.0),
    "live.slider":   (39.0, 87.0),
    "live.numbox":   (56.0, 15.0),
    "live.toggle":   (15.0, 15.0),
    "live.button":   (15.0, 15.0),
    "live.text":     (44.0, 15.0),
    "live.menu":     (100.0, 15.0),
    "live.tab":      (100.0, 20.0),
    "live.meter~":   (5.0, 100.0),
    "live.gain~":    (48.0, 136.0),
    "live.scope~":   (131.0, 131.0),
    # Max for Live visual widgets (added)
    "live.arrows":   (54.0, 15.0),
    "live.comment":  (150.0, 18.0),
    "live.drop":     (140.0, 50.0),
    "live.grid":     (240.0, 165.0),
    "live.line":     (100.0, 35.0),
    "live.step":     (240.0, 60.0),
    # Bundle-verified UI widgets (review C5, Q13): per-axis median of the
    # patching_rect Max 9.2.0 saved (markup is text-bearing -> text-sized)
    "jit.fpsgui":    (80.0, 36.0),
    "jit.playlist":  (226.0, 41.0),
    "jit.pworld":    (640.0, 360.0),
    "plot~":         (259.0, 155.0),
    "mc.ezdac~":     (45.0, 45.0),
    "mc.live.gain~": (136.0, 47.0),
    "markup":        None,
    "v8ui":          (99.0, 90.0),
    "v8.codebox":    (426.0, 258.0),
    "live.adsrui":   (104.7, 50.0),
    "mc.number~":    (75.0, 35.0),
    "itable":        (238.0, 145.0),
    "multirange":    (365.0, 160.0),
    "gridmeter~":    (129.0, 30.0),
    "node.codebox":  (524.0, 301.0),
    "text.codebox":  (535.0, 200.0),
    "zplane~":       (256.0, 256.0),
    "progress":      (32.0, 32.0),
    # Text-based UI objects
    "comment":       None,
    "message":       None,
}

# Comment box height (slightly shorter than newobj/message)
COMMENT_HEIGHT = 20.0


def text_width(text: str, maxclass: str = "newobj") -> float:
    """Return the rendered width of a MAX object given its full text.

    Use this to compute layout positions that account for actual object widths.
    Works for newobj, comment, message, and any text-based box.

    Example:
        w = text_width("prepend mallet_hardness")  # -> 177.0
        next_col_x = prev_col_x + w + H_GUTTER
    """
    w, _ = calculate_box_size(text, maxclass)
    return w


def calculate_box_size(text: str, maxclass: str) -> tuple[float, float]:
    """Calculate box dimensions for a MAX object.

    For UI objects with fixed sizes, returns the standard (width, height).
    For text-based objects (newobj, comment, message, or UI objects with None size),
    computes width from text length.

    Args:
        text: The display text of the object (e.g., "cycle~ 440").
        maxclass: The resolved maxclass (e.g., "newobj", "toggle", "comment").

    Returns:
        (width, height) as floats.
    """
    # Check if it's a UI object with a fixed size
    if maxclass in UI_SIZES:
        fixed_size = UI_SIZES[maxclass]
        if fixed_size is not None:
            return fixed_size

    # Width override lookup for newobj boxes
    if maxclass == "newobj" and text:
        parts = text.split()
        obj_name = parts[0]
        arg_count = len(parts) - 1
        overrides = _WIDTH_OVERRIDES.get(obj_name)
        if overrides:
            override_width = overrides.get(str(arg_count)) or overrides.get("default")
            if override_width:
                text_width = len(text) * CHAR_WIDTH + PADDING
                return (max(override_width, text_width), DEFAULT_HEIGHT)

    # Text-based sizing: newobj, comment, message, or UI objects with None size
    width = len(text) * CHAR_WIDTH + PADDING
    width = max(width, MIN_BOX_WIDTH)

    if maxclass == "comment":
        height = COMMENT_HEIGHT
    else:
        height = DEFAULT_HEIGHT

    return (width, height)


# ---------------------------------------------------------------------------
# Rendered geometry (Q27 / F5): one model for layout, add_box and the critic
# ---------------------------------------------------------------------------

_LINE_SPLIT = re.compile(r"\r\n|\r|\n")

# Comment keys that make MAX paint a fill behind the text: such a comment
# covers at least its stored rect.
_COMMENT_FILL_KEYS = ("bgcolor", "bgfillcolor", "grad1")


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _box_fields(box: Any) -> tuple[Any, Any, Any, Any, dict]:
    """Return (maxclass, text, patching_rect, fontsize, attrs) of a Box or a
    raw box dict (a ``{"box": {...}}`` wrapper is unwrapped)."""
    if isinstance(box, dict):
        inner = box.get("box")
        if isinstance(inner, dict) and "patching_rect" not in box:
            box = inner
        return (box.get("maxclass"), box.get("text"), box.get("patching_rect"),
                box.get("fontsize"), box)
    attrs = getattr(box, "extra_attrs", None)
    if not isinstance(attrs, dict):
        attrs = {}
    return (getattr(box, "maxclass", None), getattr(box, "text", None),
            getattr(box, "patching_rect", None), getattr(box, "fontsize", None),
            attrs)


def rendered_rect(box: Any, *, max_saved: bool = False) -> list[float] | None:
    """Return the rect a box actually covers in MAX as a new [x, y, w, h].

    The single rendered-geometry model shared by apply_layout, the add_box
    overlap check and the layout critic's overlap check (Q27 / F5).

    - **message**: ``max(stored w, longest line * 8 + 25)`` (CLAUDE.md
      Rule #4), lines split on ``\\r`` / ``\\n``. With ``max_saved=True`` the
      stored width is kept: MAX normalises message geometry when it saves.
    - **comment**: the text extent. Each paragraph is ``len * 5.6 * fs/12 +
      10`` px; one at or above 1.6x the stored width wraps at the stored
      width (``ceil(text / w)`` lines), otherwise it overflows as one line.
      Height is ``6 + 14 * fs/12`` per line. A comment that paints a fill
      (``bgcolor`` / ``bgfillcolor`` / ``grad1``) or a bubble covers at least
      its stored rect.
    - every other box: the stored rect, copied.

    Accepts a :class:`Box` or a raw box dict and never mutates it. Returns
    None when the rect is not at least 4 numbers. Non-str text reads as "",
    and a fontsize that is not a positive number reads as 12.
    """
    maxclass, text, rect, fontsize, attrs = _box_fields(box)
    if not isinstance(rect, (list, tuple)) or len(rect) < 4:
        return None
    if not all(_is_number(v) for v in rect[:4]):
        return None
    x, y, w, h = (float(v) for v in rect[:4])
    if not isinstance(text, str):
        text = ""
    fs = fontsize if _is_number(fontsize) and fontsize > 0 else FONT_SIZE
    scale = float(fs) / FONT_SIZE

    if maxclass == "message":
        if not max_saved:
            longest = max(len(line) for line in _LINE_SPLIT.split(text))
            w = max(w, longest * MESSAGE_CHAR_WIDTH + MESSAGE_CHROME)
        return [x, y, w, h]

    if maxclass == "comment":
        width = 0.0
        lines = 0
        for para in _LINE_SPLIT.split(text):
            tw = len(para) * COMMENT_CHAR_WIDTH * scale + COMMENT_TEXT_PAD
            if w <= 0 or tw < COMMENT_WRAP_RATIO * w:
                n, pw = 1, tw
            else:
                n, pw = int(math.ceil(tw / w)), w
            width = max(width, pw)
            lines += n
        height = COMMENT_BASE_HEIGHT + COMMENT_LINE_HEIGHT * scale * lines
        filled = any(attrs.get(k) is not None for k in _COMMENT_FILL_KEYS)
        if filled or attrs.get("bubble") == 1:
            width = max(width, w)
            height = max(height, h)
        return [x, y, width, height]

    return [x, y, w, h]


def is_max_saved(props: Any) -> bool:
    """True when a patcher was last saved by MAX rather than the generator.

    *props* is a ``Patcher.props`` dict or a raw patcher dict. The generator
    always writes ``DEFAULT_PATCHER_PROPS["appversion"]`` (9.0.0); any other
    (major, minor, revision) means MAX re-saved it. A missing or non-dict
    appversion reads as False.
    """
    if not isinstance(props, dict):
        return False
    app = props.get("appversion")
    if not isinstance(app, dict):
        return False
    ref = DEFAULT_PATCHER_PROPS["appversion"]
    keys = ("major", "minor", "revision")
    return tuple(app.get(k) for k in keys) != tuple(ref[k] for k in keys)
