"""Aesthetic styling helpers for MAX patcher generation.

Provides palette access, canvas background setting, object background
color helpers, and panel auto-sizing.
All colors come from AESTHETIC_PALETTE in defaults.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from src.maxpat.defaults import (
    AESTHETIC_PALETTE,
    MAX_DEFAULT_PANEL_BG,
    MAX_THEME_BOX_FILL,
    MAX_THEME_CANVAS_BG,
    MIN_CONTRAST_RATIO,
    MIN_VISIBLE_FILL_ALPHA,
)

if TYPE_CHECKING:
    from src.maxpat.patcher import Box, Patcher


# Candidate text colors the generator is allowed to assign, dark first.
# Tie-breaking iterates this order and only accepts a strict improvement, so
# an exact tie resolves to the dark candidate.
TEXT_COLOR_CANDIDATES: tuple[list[float], ...] = (
    [0.20, 0.20, 0.25, 1.0],   # dark
    [0.80, 0.80, 0.82, 1.0],   # light
)

# Tried only when both TEXT_COLOR_CANDIDATES fail MIN_CONTRAST_RATIO (Q26 /
# E7): on a mid-gray surface neither the dark nor the light candidate reaches
# 4.5:1, but pure black or white may.
FALLBACK_TEXT_CANDIDATES: tuple[list[float], ...] = (
    [0.0, 0.0, 0.0, 1.0],      # black
    [1.0, 1.0, 1.0, 1.0],      # white
)


def relative_luminance(rgba: list[float]) -> float:
    """WCAG 2.1 relative luminance of an sRGB color.

    Each channel is linearized (divided by 12.92 below the 0.03928 knee,
    otherwise ``((c + 0.055) / 1.055) ** 2.4``) and then weighted
    0.2126 / 0.7152 / 0.0722. Alpha is ignored.

    Args:
        rgba: RGBA (or RGB) color with channels in [0.0, 1.0].

    Returns:
        Relative luminance in [0.0, 1.0].
    """
    lin = []
    for c in rgba[:3]:
        c = min(max(float(c), 0.0), 1.0)
        lin.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_ratio(fg: list[float], bg: list[float]) -> float:
    """WCAG 2.1 contrast ratio between two colors.

    ``(lighter + 0.05) / (darker + 0.05)`` over the two relative luminances.
    Symmetric in its arguments; ranges from 1.0 (identical) to 21.0
    (black on white).
    """
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def best_text_color(
    backgrounds: list[list[float]],
    candidates: tuple[list[float], ...] | list[list[float]] | None = None,
) -> list[float]:
    """Pick the text color that reads best across a set of candidate backgrounds.

    Pass a single-element list when the background is known. Pass several when
    the background is indeterminate (e.g. an uncolored panel, where MAX's real
    fill is not discoverable -- see MAX_DEFAULT_PANEL_BG). The chosen candidate
    maximizes the MINIMUM contrast ratio across ``backgrounds``, so an
    indeterminate surface still gets the least-bad color rather than one that
    happens to be right for a guess.

    Ties break toward the dark candidate.

    Args:
        backgrounds: One or more RGBA backgrounds to read against.
        candidates: Text colors to choose from. Defaults to
            TEXT_COLOR_CANDIDATES.

    Returns:
        A new RGBA list (never a shared reference to a module constant).
    """
    cands = TEXT_COLOR_CANDIDATES if candidates is None else candidates
    if not backgrounds:
        return list(cands[0])

    best = None
    best_score = float("-inf")
    for cand in cands:
        score = min(contrast_ratio(cand, bg) for bg in backgrounds)
        if score > best_score:
            best_score = score
            best = cand
    return list(best)


def choose_text_color(current, backgrounds: list[list[float]]) -> tuple[list[float], bool]:
    """The generator's text color for one box: ``(color, kept)`` (Q26 / E7).

    * An explicit *current* color that already reaches MIN_CONTRAST_RATIO
      against every background is kept (``kept`` True), so a deliberate
      palette color such as ``header_color`` survives.
    * Otherwise ``best_text_color(backgrounds)`` over TEXT_COLOR_CANDIDATES
      (dark / light), when that passes.
    * Only when both fail, the best of dark, light, black and white
      (FALLBACK_TEXT_CANDIDATES), e.g. black on a mid-gray 0.5 panel.

    A missing or invalid *current* is always filled.
    """
    if not backgrounds:
        if is_valid_color(current):
            return list(current), True
        return list(TEXT_COLOR_CANDIDATES[0]), False

    def score(color) -> float:
        return min(contrast_ratio(color, bg) for bg in backgrounds)

    if is_valid_color(current) and score(current) >= MIN_CONTRAST_RATIO:
        return list(current), True
    best = best_text_color(backgrounds)
    if score(best) >= MIN_CONTRAST_RATIO:
        return best, False
    every = tuple(TEXT_COLOR_CANDIDATES) + tuple(FALLBACK_TEXT_CANDIDATES)
    return best_text_color(backgrounds, every), False


def set_canvas_background(
    patcher: Patcher,
    color: list[float] | None = None,
) -> None:
    """Set patcher canvas background color.

    Sets bgcolor, editing_bgcolor (unlocked mode) and locked_bgcolor (locked
    mode) to the same color for visual consistency.

    ``bgcolor`` is the patcher-level key MAX honors for locked and presentation
    mode (finding F-1: 11 of MAX's own shipped patchers set it, vs 2 setting
    editing_bgcolor). Leaving it unset makes MAX fall back to its light default
    while generator-side contrast logic assumes the dark canvas.

    Args:
        patcher: The Patcher instance to style.
        color: Custom RGBA color list. Defaults to AESTHETIC_PALETTE["canvas_bg"].
    """
    bg = color if color is not None else AESTHETIC_PALETTE["canvas_bg"]
    patcher.props["bgcolor"] = list(bg)
    patcher.props["editing_bgcolor"] = list(bg)
    patcher.props["locked_bgcolor"] = list(bg)


def set_object_bgcolor(
    box: Box,
    palette_key: str | None = None,
    color: list[float] | None = None,
) -> None:
    """Apply background color to a Box via extra_attrs.

    One of palette_key or color must be provided. If both are provided,
    palette_key takes precedence.

    Args:
        box: The Box instance to style.
        palette_key: Key in AESTHETIC_PALETTE to use for the color.
        color: Custom RGBA color list.

    Raises:
        ValueError: If neither palette_key nor color is provided.
    """
    if palette_key is not None:
        box.extra_attrs["bgcolor"] = list(AESTHETIC_PALETTE[palette_key])
    elif color is not None:
        box.extra_attrs["bgcolor"] = list(color)
    else:
        raise ValueError("One of palette_key or color must be provided")


def auto_size_panel(
    boxes: list[Box],
    padding: float = 18.0,
) -> tuple[float, float, float, float]:
    """Compute bounding box for a panel enclosing the given boxes.

    Returns (x, y, width, height) where the panel surrounds all boxes
    with the specified padding on every side.

    Args:
        boxes: List of Box instances to enclose. Each must have patching_rect.
        padding: Padding in pixels added on all four sides.

    Returns:
        (x, y, width, height) tuple. Returns (0.0, 0.0, 0.0, 0.0) if
        boxes is empty.
    """
    if not boxes:
        return (0.0, 0.0, 0.0, 0.0)

    min_x = min(b.patching_rect[0] for b in boxes)
    min_y = min(b.patching_rect[1] for b in boxes)
    max_x = max(b.patching_rect[0] + b.patching_rect[2] for b in boxes)
    max_y = max(b.patching_rect[1] + b.patching_rect[3] for b in boxes)

    return (
        min_x - padding,
        min_y - padding,
        (max_x - min_x) + 2 * padding,
        (max_y - min_y) + 2 * padding,
    )


_AUTO_HIGHLIGHT = {
    "dac~": "emphasis_dac",
    "ezdac~": "emphasis_dac",
    "loadbang": "emphasis_loadbang",
}


def apply_auto_styling(patcher: Patcher, *, contrast: bool = True) -> None:
    """Apply default aesthetic styling to a patcher.

    Sets the canvas background color and highlights special objects
    (dac~, ezdac~, loadbang) with subtle palette colors. Skips boxes
    that already have a user-set bgcolor. Then runs ensure_text_contrast
    unless *contrast* is False: finalize_patch(is_new=True) passes False
    and resolves contrast once, after layout has moved panels and labels
    onto their final surfaces (Q27 / F3).
    """
    set_canvas_background(patcher)
    for box in patcher.boxes:
        palette_key = _AUTO_HIGHLIGHT.get(box.name)
        if palette_key and "bgcolor" not in box.extra_attrs:
            set_object_bgcolor(box, palette_key=palette_key)
    if contrast:
        ensure_text_contrast(patcher)


def _point_in_rect(px: float, py: float, rect: list[float]) -> bool:
    """Check if point (px, py) is inside [x, y, w, h] rect."""
    x, y, w, h = rect[:4]
    return x <= px <= x + w and y <= py <= y + h


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _valid_rect(rect) -> bool:
    """True for an ``[x, y, w, h]`` list of numbers (extra entries ignored)."""
    return isinstance(rect, (list, tuple)) and len(rect) >= 4 and all(_is_num(v) for v in rect[:4])


def is_valid_color(color) -> bool:
    """True for an RGB(A) list whose first three entries are numbers."""
    return (
        isinstance(color, (list, tuple))
        and len(color) >= 3
        and all(_is_num(v) for v in color[:3])
    )


def fill_is_visible(color) -> bool:
    """True when *color* is a valid fill with alpha >= MIN_VISIBLE_FILL_ALPHA.

    A missing alpha counts as opaque. Transparent or invalid fills let the
    surface beneath show through (Q26 / E7).
    """
    if not is_valid_color(color):
        return False
    alpha = color[3] if len(color) >= 4 and _is_num(color[3]) else 1.0
    return alpha >= MIN_VISIBLE_FILL_ALPHA


# Fill attribute keys a box may carry (resolve_fill_color's encodings).
_FILL_KEYS = ("bgfillcolor", "grad1", "bgcolor")

# Classes whose refpages document ``bgfillcolor``, the theme's box-fill key: a
# box of one of these with NO fill attribute renders on MAX_THEME_BOX_FILL.
THEME_FILL_MAXCLASSES = frozenset({"newobj", "message", "umenu"})

# Classes that draw their text straight onto whatever lies beneath them
# (review 261022-ud6 WR-07). Every other text-bearing class paints its own
# background (bach.roll's white staff, jit.cellblock, textedit, textbutton,
# live.* displays, ...).
TRANSPARENT_TEXT_MAXCLASSES = frozenset({"comment", "live.comment"})


def paints_unknown_background(maxclass: str | None, attrs: dict) -> bool:
    """True when a box paints its own background in a colour we cannot know.

    That is a class outside TRANSPARENT_TEXT_MAXCLASSES and
    THEME_FILL_MAXCLASSES with no visible fill attribute: e.g. a
    ``bach.roll`` (white by default), whose explicit textcolor must not be
    scored against the panel or canvas behind it (WR-07). Contrast passes
    leave such boxes alone. A box with a visible fill attribute resolves to
    that fill ("own") and returns False.
    """
    if maxclass in TRANSPARENT_TEXT_MAXCLASSES or maxclass in THEME_FILL_MAXCLASSES:
        return False
    own = resolve_fill_color(attrs) if isinstance(attrs, dict) else None
    if own is not None and fill_is_visible(own):
        return False
    return maxclass is not None


def gradient_stops(attrs: dict) -> list | None:
    """Both stops of a gradient fill, or None (review 261022-ud6 WR-07).

    Encodings: a ``bgfillcolor`` dict (plain or list-wrapped) with
    ``type: "gradient"`` and valid ``color1`` / ``color2``; else a panel in
    gradient ``mode: 1`` with valid ``grad1`` / ``grad2``. Text over a
    gradient has to read on both ends.
    """
    if not isinstance(attrs, dict):
        return None
    fill = _unwrap_fill(attrs.get("bgfillcolor"))
    if isinstance(fill, dict) and fill.get("type") == "gradient":
        c1, c2 = fill.get("color1"), fill.get("color2")
        if is_valid_color(c1) and is_valid_color(c2):
            return [list(c1), list(c2)]
    if attrs.get("mode") == 1:
        g1, g2 = attrs.get("grad1"), attrs.get("grad2")
        if is_valid_color(g1) and is_valid_color(g2):
            return [list(g1), list(g2)]
    return None


class ResolvedBackground(NamedTuple):
    """A background color plus whether it was FOUND or ASSUMED.

    ``assumed=True`` means no color encoding was present and
    MAX_DEFAULT_PANEL_BG stood in for it. Callers must treat that case as
    indeterminate: feed the assumed color together with the surrounding
    surface into ``best_text_color()``, and downgrade critic findings to a
    ``note``.
    """

    color: list[float]
    assumed: bool


class _GradientBackground(ResolvedBackground):
    """A ResolvedBackground (``color`` = first stop) that also carries
    ``stops``, both gradient stops. Built only by
    ``build_panel_layers(..., gradients=True)``; equal to the plain
    ResolvedBackground of its first stop."""


def _with_stops(color: list[float], assumed: bool, stops) -> ResolvedBackground:
    if not stops:
        return ResolvedBackground(list(color), assumed)
    bg = _GradientBackground(list(color), assumed)
    bg.stops = [list(s) for s in stops]
    return bg


def _unwrap_fill(value):
    """A list/tuple whose first element is a dict (MAX's list-wrapped fill,
    e.g. ``generic_editor.maxpat``) unwraps to that dict (Q27 / F6)."""
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], dict):
        return value[0]
    return value


def _fill_from_value(value) -> list[float] | None:
    """A valid color from one fill attribute value, or None.

    A dict (plain or list-wrapped) reads ``color1``, else ``color``; a plain
    list must itself be a valid color.
    """
    value = _unwrap_fill(value)
    if isinstance(value, dict):
        for key in ("color1", "color"):
            found = value.get(key)
            if is_valid_color(found):
                return list(found)
        return None
    if is_valid_color(value):
        return list(value)
    return None


def resolve_fill_color(attrs: dict) -> list[float] | None:
    """Read a fill color out of a plain MAX attribute dict, or None.

    Takes a PLAIN dict so both entry points share one implementation:
    ``Box.extra_attrs`` on the object side, and the raw box dict on the
    critic side.

    Encodings, in priority order (counts from finding F-2 across this repo's
    58 generated panels):
      1. ``bgfillcolor`` dict -- ``color1``, else ``color``   (2 panels)
      2. flat top-level ``grad1``                             (37 panels)
      3. ``bgcolor``                                          (19 panels)

    A list-wrapped dict (``[{"type": "color", "color": [...]}]``, as in
    MAX's ``generic_editor.maxpat``) unwraps to that dict under any of the
    three keys, and a dict under ``grad1`` / ``bgcolor`` reads the same way
    (Q27 / F6). Only valid colors (:func:`is_valid_color`) are returned: an
    invalid value falls through to the next key, then None.
    """
    if not isinstance(attrs, dict):
        return None
    bgfill = _unwrap_fill(attrs.get("bgfillcolor"))
    if isinstance(bgfill, dict):
        found = _fill_from_value(bgfill)
        if found is not None:
            return found

    for key in ("grad1", "bgcolor"):
        found = _fill_from_value(attrs.get(key))
        if found is not None:
            return found

    return None


def resolve_panel_background(attrs: dict) -> ResolvedBackground:
    """Effective background of a panel, never None.

    Falls back to MAX_DEFAULT_PANEL_BG (flagged ``assumed=True``) when the
    panel carries no color encoding at all -- 84 of MAX's own shipped panels
    are in that state and MAX ships no discoverable default for it (F-3).
    """
    color = resolve_fill_color(attrs)
    if color is not None:
        return ResolvedBackground(color, False)
    return ResolvedBackground(list(MAX_DEFAULT_PANEL_BG), True)


def _get_panel_bgcolor(panel: Box) -> ResolvedBackground:
    """Box-object wrapper over resolve_panel_background()."""
    return resolve_panel_background(panel.extra_attrs)


def resolve_patcher_background(props) -> list[float]:
    """Effective patcher background from a patcher props / patcher dict.

    ``bgcolor`` (what MAX honors in locked and presentation mode), then
    ``editing_bgcolor``, then ``locked_bgcolor``; with none of them valid,
    the Max 9 theme canvas MAX_THEME_CANVAS_BG (0.235; Q26 / E7). One
    helper serves the critic and the generator.
    """
    if isinstance(props, dict):
        for key in ("bgcolor", "editing_bgcolor", "locked_bgcolor"):
            value = props.get(key)
            if is_valid_color(value):
                return list(value)
    return list(MAX_THEME_CANVAS_BG)


def build_panel_layers(entries, *, gradients: bool = False) -> tuple[list, list]:
    """Z-ordered panel layers for contrast resolution (Q26 / E7, PD-6).

    ``gradients`` (keyword-only; review 261022-ud6 WR-07): when True, a
    gradient panel (:func:`gradient_stops`) carries both stops, and
    :func:`resolve_effective_background` scores text against both. The
    contrast passes set it; the default keeps the first-stop resolution.

    *entries* is an iterable of ``(attrs, patching_rect, presentation,
    presentation_rect)`` for every panel, in box-array order. Returns
    ``(patching_layers, presentation_layers)``: lists of ``(rect,
    ResolvedBackground)`` topmost first. Foreground-layer panels
    (``background`` != 1) come before ``background: 1`` panels; within each
    layer box-array order holds, index 0 topmost (CLAUDE.md Rule #6). A
    panel whose found fill is invisible (alpha below MIN_VISIBLE_FILL_ALPHA,
    or malformed) is left out; an uncolored panel keeps the assumed
    MAX_DEFAULT_PANEL_BG handling. Only panels in presentation with a
    presentation_rect enter the presentation layer; invalid rects are
    dropped.
    """
    front: list = []
    back: list = []
    for entry in entries:
        try:
            attrs, patching_rect, presentation, presentation_rect = entry
        except (TypeError, ValueError):
            continue
        if not isinstance(attrs, dict):
            continue
        found = resolve_fill_color(attrs)
        if found is not None:
            if not fill_is_visible(found):
                continue
            stops = gradient_stops(attrs) if gradients else None
            bg = _with_stops(found, False, stops)
        else:
            bg = ResolvedBackground(list(MAX_DEFAULT_PANEL_BG), True)
        layer = back if attrs.get("background") == 1 else front
        layer.append((patching_rect, presentation, presentation_rect, bg))
    ordered = front + back
    patching_layers = [
        (list(r[:4]), bg) for r, _, _, bg in ordered if _valid_rect(r)
    ]
    presentation_layers = [
        (list(pr[:4]), bg) for _, pres, pr, bg in ordered
        if pres and _valid_rect(pr)
    ]
    return patching_layers, presentation_layers


def _bg_under_rect(
    rect: list[float] | None,
    panel_layers: list[tuple[list[float] | None, ResolvedBackground]],
    fallback: list[float],
) -> ResolvedBackground | None:
    """Background visible beneath the center of ``rect`` in one coordinate space.

    ``panel_layers`` is a list of (panel_rect, ResolvedBackground) topmost
    first (:func:`build_panel_layers`); the FIRST containing panel wins
    (Q26 / E7). Returns None when ``rect`` is not a valid rect (the box is
    absent from that space).
    """
    if not _valid_rect(rect):
        return None
    cx = rect[0] + rect[2] * 0.5
    cy = rect[1] + rect[3] * 0.5
    for panel_rect, panel_bg in panel_layers:
        if not _valid_rect(panel_rect):
            continue
        if _point_in_rect(cx, cy, panel_rect):
            return _with_stops(
                panel_bg.color, panel_bg.assumed, getattr(panel_bg, "stops", None)
            )
    return ResolvedBackground(list(fallback), False)


class BackgroundResolution(NamedTuple):
    """Everything a caller needs to choose and justify a text color."""

    color: list[float]          # the effective background
    assumed: bool               # True when the color is a documented guess
    space: str                  # "own" | "presentation" | "patching"
    candidates: list[list[float]]   # backgrounds to feed best_text_color()
    patching_color: list[float] | None  # patching-space bg, for D-1 notes


# A box is a contrast target if it is a comment, or if it already carries a
# generator-set textcolor (this is what pulls in add_step_marker's textbutton
# while leaving plain objects like `toggle` alone).
_TEXT_BEARING_MAXCLASSES = frozenset({"comment"})


def is_text_contrast_target(maxclass: str | None, attrs: dict) -> bool:
    """Whether a box's text color is the generator's to control."""
    if maxclass in _TEXT_BEARING_MAXCLASSES:
        return True
    return "textcolor" in attrs


def resolve_effective_background(
    attrs: dict,
    patching_rect: list[float] | None,
    presentation: bool,
    presentation_rect: list[float] | None,
    patching_layers: list[tuple[list[float] | None, ResolvedBackground]],
    presentation_layers: list[tuple[list[float] | None, ResolvedBackground]],
    patcher_bg: list[float],
    *,
    maxclass: str | None = None,
) -> BackgroundResolution:
    """Resolve the background a box's text actually renders over.

    Precedence:
      1. D-2 -- the box's OWN background, if it paints a visible one
         (alpha >= MIN_VISIBLE_FILL_ALPHA; Q26 / E7). A box that paints its
         own background IS its own background, in both coordinate spaces. A
         *maxclass* in THEME_FILL_MAXCLASSES (newobj, message, umenu) with
         NO fill attribute at all paints the theme box fill
         MAX_THEME_BOX_FILL (0.172). A transparent fill falls through.
      2. Presentation space, when the box is in presentation (D-1: presentation
         is the user-facing surface, so it decides on conflict).
      3. Patching space.

    Layers come from :func:`build_panel_layers` (topmost first; the first
    containing panel wins). When the winning background was assumed rather
    than found, the canvas is added as a second candidate so
    ``best_text_color`` can maximize the worst case across both plausible
    surfaces.
    """
    own = resolve_fill_color(attrs)
    if own is not None and fill_is_visible(own):
        return BackgroundResolution(list(own), False, "own", [list(own)], list(own))
    if (
        own is None
        and maxclass in THEME_FILL_MAXCLASSES
        and not any(key in attrs for key in _FILL_KEYS)
    ):
        fill = list(MAX_THEME_BOX_FILL)
        return BackgroundResolution(fill, False, "own", [list(fill)], list(fill))

    patching_bg = _bg_under_rect(patching_rect, patching_layers, patcher_bg)

    if presentation and presentation_rect:
        primary = _bg_under_rect(presentation_rect, presentation_layers, patcher_bg)
        space = "presentation"
    else:
        primary = patching_bg
        space = "patching"

    if primary is None:
        primary = ResolvedBackground(list(patcher_bg), False)

    stops = getattr(primary, "stops", None)
    if stops:
        # Gradient panel (layers built with gradients=True): both stops.
        candidates = [list(s) for s in stops]
    else:
        candidates = [list(primary.color)]
    if primary.assumed and list(patcher_bg) != list(primary.color):
        candidates.append(list(patcher_bg))

    return BackgroundResolution(
        list(primary.color),
        primary.assumed,
        space,
        candidates,
        list(patching_bg.color) if patching_bg is not None else None,
    )


def _set_textcolor(box: Box, color: list[float]) -> None:
    """Write a resolved textcolor to the box's ``extra_attrs``.

    New boxes serialize ``extra_attrs`` directly; on a round-tripped box
    (``_raw`` populated) ``Patcher.to_dict()`` writes back every
    ``extra_attrs`` key changed since load, so the colour reaches disk on
    both paths (Q28; CLAUDE.md Rule #5).
    """
    box.extra_attrs["textcolor"] = list(color)


def _apply_text_contrast(
    patcher: Patcher, *, only_ids=None, explicit_only: bool = False
) -> int:
    """Shared engine behind ensure_text_contrast() and repair_text_contrast().

    Panel layers and the patcher background come from the same helpers the
    layout critic uses (:func:`build_panel_layers`,
    :func:`resolve_patcher_background`; Q26 / E7). Each box's color comes
    from :func:`choose_text_color`; only changed colors are written and
    counted. Returns the number of boxes whose textcolor changed.

    Review 261022-ud6 WR-07:

    - a box that paints its own background in an unknown colour
      (:func:`paints_unknown_background`: bach.roll, jit.cellblock, a
      textbutton without a fill, ...) is skipped -- its text sits on its
      own surface, not on the panel behind it;
    - over a gradient panel the text is scored against both stops
      (:func:`gradient_stops`); when no candidate reads on both, an
      explicit textcolor is kept rather than swapped for another colour
      that also fails.

    ``only_ids`` (private, keyword-only; Q36 / D-03): when not None, only
    top-level boxes whose id is in it are considered; panel layers and the
    patcher background still come from every panel. ``explicit_only``
    (private, keyword-only; locked decision B11): only boxes that already
    carry a ``textcolor`` are considered -- a comment without one renders
    in MAX's theme text colour and is never given one. ``edit_patch``
    sessions pass both, with the ids of the boxes the edit added, so an
    approved patch is never restyled. The public wrappers pass neither.
    """
    panels = [b for b in patcher.boxes if b.maxclass == "panel"]
    patcher_bg = resolve_patcher_background(patcher.props)

    patching_layers, presentation_layers = build_panel_layers(
        (
            (p.extra_attrs, p.patching_rect, p.presentation, p.presentation_rect)
            for p in panels
        ),
        gradients=True,
    )

    changed = 0
    for box in patcher.boxes:
        if only_ids is not None and box.id not in only_ids:
            continue
        if box.maxclass == "panel":
            continue
        if explicit_only and "textcolor" not in box.extra_attrs:
            continue
        if not is_text_contrast_target(box.maxclass, box.extra_attrs):
            continue
        if paints_unknown_background(box.maxclass, box.extra_attrs):
            continue

        resolution = resolve_effective_background(
            box.extra_attrs,
            box.patching_rect,
            box.presentation,
            box.presentation_rect,
            patching_layers,
            presentation_layers,
            patcher_bg,
            maxclass=box.maxclass,
        )
        current = box.extra_attrs.get("textcolor")
        color, _kept = choose_text_color(current, resolution.candidates)
        if (
            len(resolution.candidates) > 1
            and not resolution.assumed
            and is_valid_color(current)
            and min(contrast_ratio(color, bg) for bg in resolution.candidates)
            < MIN_CONTRAST_RATIO
        ):
            # Gradient with no colour that reads on both stops: keep the
            # explicit choice (indeterminate, WR-07).
            continue
        if current == color:
            continue
        changed += 1
        _set_textcolor(box, color)

    return changed


def ensure_text_contrast(patcher: Patcher) -> None:
    """Set textcolor on text boxes for readability against their real background.

    The effective background is resolved per box, in this precedence order:

    - The box's OWN background, if it paints one (D-2). ``add_section_header``
      pairs a light ``header_bgcolor`` with its text; that pairing, not the
      dark canvas behind it, is what the reader sees.
    - Presentation space: the box's ``presentation_rect`` center against the
      ``presentation_rect`` of panels that are themselves in presentation.
    - Patching space: the box's ``patching_rect`` center against each panel's
      ``patching_rect``.

    Backgrounds fall back to the patcher background (``bgcolor``, then the two
    editing-specific keys, then the Max 9 theme canvas 0.235) when no panel
    contains the box. Panels are read topmost first: foreground-layer panels
    before ``background: 1`` panels, box order within each layer; the first
    containing panel wins and fills with alpha below MIN_VISIBLE_FILL_ALPHA
    are skipped (Q26 / E7).

    An explicit textcolor that already passes MIN_CONTRAST_RATIO against the
    resolved background is kept; a missing one is always filled; black and
    white are tried only when both the dark and the light candidate fail
    (:func:`choose_text_color`).

    When a box exists in both spaces and the two demand opposite text colors,
    the PRESENTATION result wins (locked decision D-1): presentation is the
    user-facing surface, so a patching-mode compromise is the acceptable half
    of the trade. The layout critic surfaces that compromise as a ``note`` so
    it is visible rather than silent.

    Colors are chosen by WCAG contrast ratio, not by a luminance>0.5 flip. A
    semantic tier color (header, subsection, annotation) is replaced only
    when it fails, because readability trumps cosmetic coloring.

    Args:
        patcher: The Patcher instance to process.
    """
    _apply_text_contrast(patcher)


def repair_text_contrast(patcher: Patcher) -> int:
    """Recompute text contrast on an ALREADY-LOADED patcher. Opt-in only.

    This is deliberately NOT wired into any automatic path (locked decision
    D-4). ``hooks.finalize_patch()`` runs ``apply_auto_styling`` -- and hence
    ``ensure_text_contrast`` -- only when ``is_new=True``, so editing an
    existing patch never silently restyles it. Call this explicitly, per
    patch, when you want an existing patch repaired.

    Args:
        patcher: A Patcher, typically from ``Patcher.from_dict(read_patch(...))``.

    Same resolution as ensure_text_contrast (Q26 / E7): passing explicit
    colors are kept, so a patch whose text already reads returns 0.

    Returns:
        Number of boxes whose textcolor changed. Idempotent: a second call on
        an unchanged patcher returns 0.
    """
    return _apply_text_contrast(patcher)
