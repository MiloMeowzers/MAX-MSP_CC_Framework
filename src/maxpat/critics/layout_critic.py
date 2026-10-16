"""Layout critic -- validates physical layout of boxes and cables.

Catches layout quality issues that the mechanical validation pipeline
does not detect:
  - Overlapping boxes (accounting for COLLISION_PAD)
  - Missing cable midpoints on offset/upward cables
  - Out-of-bounds placement (negative coordinates)

Every scope of the shared :class:`src.maxpat.graph.PatchGraph` is checked
on its own boxes and cords, gen scopes included (Q20); nested findings carry
``CriticResult.path`` and a ``[p synth] `` prefix. Text contrast resolves
against each scope's own patcher background (``bgcolor`` /
``editing_bgcolor`` / ``locked_bgcolor``, else the Max 9 theme canvas 0.235)
and reads a missing textcolor as the theme text color 0.85 (Q26 / E7), and
presentation coverage is active per scope when that scope has a
presentation box.
"""

from __future__ import annotations

from src.maxpat import walk
from src.maxpat.critics.base import CriticResult, tag_results
from src.maxpat.graph import PatchGraph
from src.maxpat.defaults import AESTHETIC_PALETTE, HORIZONTAL_THRESHOLD, UPWARD_BUS_THRESHOLD
from src.maxpat.sizing import is_max_saved, rendered_rect

# Collision padding from Phase 15-02 decision: 5px around all boxes
COLLISION_PAD = 5.0

# Decorative/background maxclasses excluded from overlap checks
_DECORATIVE_MAXCLASSES = frozenset({"comment", "panel"})

# A box with ignoreclick=1 whose stored rect lies inside another box's
# stored rect (within this tolerance) is a deliberate overlay readout
# (add_overlay_readout; Q27 / F5), not an accidental overlap.
_OVERLAY_TOLERANCE = 2.0

# Margin from box edge to first/last inlet/outlet center (matches layout.py)
_IO_MARGIN = 7.0


def review_layout(patch_dict: dict, *, graph: "PatchGraph | None" = None) -> list[CriticResult]:
    """Review physical layout of a patch for readability issues.

    Checks:
      1. Overlapping boxes (rendered rects with COLLISION_PAD, excluding
         comments/panels and deliberate ignoreclick overlays; message widths
         follow ``sizing.rendered_rect``, with stored widths when the
         top-level patcher was MAX-saved)
      2. Missing cable midpoints on offset/upward cables
      3. Out-of-bounds placement (negative x or y)

    Args:
        patch_dict: A .maxpat-format dict.
        graph: The shared PatchGraph of *patch_dict* (review_patch passes
            it); built here when None.

    Returns:
        List of CriticResult findings, top level first, nested scopes in
        pre-order.
    """
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    results: list[CriticResult] = []
    top = patch_dict.get("patcher") if isinstance(patch_dict, dict) else None
    max_saved = is_max_saved(top)
    for scope in graph.scopes:
        box_list = scope.box_list
        found: list[CriticResult] = []
        found.extend(_check_overlapping_boxes(box_list, max_saved=max_saved))
        found.extend(_check_missing_midpoints(scope.boxes, scope.edges))
        found.extend(_check_out_of_bounds(box_list))
        found.extend(_check_text_contrast(box_list, scope.patcher))
        found.extend(_check_presentation_coverage(box_list))
        results.extend(tag_results(found, scope.path))
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rects_overlap(r1: list[float], r2: list[float], pad: float) -> bool:
    """Check if two AABB rects are closer than ``pad`` pixels apart.

    Each rect is [x, y, width, height]. ``pad`` is the minimum required
    gap between the two rects -- if the gap on any axis is less than
    ``pad``, they are considered overlapping. We expand only one rect
    by half ``pad`` on each side (equivalent to Minkowski sum with a
    pad/2 border on each rect).
    """
    x1, y1, w1, h1 = r1
    x2, y2, w2, h2 = r2

    half = pad * 0.5

    # Expand rect1 by half-pad on each side
    left1, right1 = x1 - half, x1 + w1 + half
    top1, bottom1 = y1 - half, y1 + h1 + half
    # Expand rect2 by half-pad on each side
    left2, right2 = x2 - half, x2 + w2 + half
    top2, bottom2 = y2 - half, y2 + h2 + half

    # AABB overlap test: overlap if no separation on any axis
    if right1 <= left2 or right2 <= left1:
        return False
    if bottom1 <= top2 or bottom2 <= top1:
        return False
    return True


def _outlet_x(box: dict, outlet_idx: int) -> float:
    """Approximate x position of an outlet on a box (raw dict version)."""
    rect = box.get("patching_rect", [0, 0, 60, 22])
    x = rect[0]
    w = rect[2]
    n = box.get("numoutlets", 1)
    if n <= 1:
        return x + _IO_MARGIN  # MAX draws a lone port at the left edge, not centered
    usable = w - 2 * _IO_MARGIN
    spacing = usable / (n - 1)
    return x + _IO_MARGIN + outlet_idx * spacing


def _inlet_x(box: dict, inlet_idx: int) -> float:
    """Approximate x position of an inlet on a box (raw dict version)."""
    rect = box.get("patching_rect", [0, 0, 60, 22])
    x = rect[0]
    w = rect[2]
    n = box.get("numinlets", 1)
    if n <= 1:
        return x + _IO_MARGIN  # MAX draws a lone port at the left edge, not centered
    usable = w - 2 * _IO_MARGIN
    spacing = usable / (n - 1)
    return x + _IO_MARGIN + inlet_idx * spacing


def _box_label(box: dict) -> str:
    """Human-readable label for a box: the first text token, else the
    maxclass, else ``unknown`` (whitespace or non-str text never raises)."""
    tokens = walk.box_tokens(box)
    if tokens:
        return tokens[0]
    return walk.box_maxclass(box) or "unknown"


# ---------------------------------------------------------------------------
# Check 1: Overlapping boxes
# ---------------------------------------------------------------------------

def _stored_rect(box: dict) -> list[float] | None:
    """The box's stored patching_rect as 4 floats, or None when invalid."""
    rect = box.get("patching_rect")
    if not isinstance(rect, (list, tuple)) or len(rect) < 4:
        return None
    vals = rect[:4]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        return None
    return [float(v) for v in vals]


def _inside(inner: list[float], outer: list[float], tol: float) -> bool:
    """True when *inner* lies inside *outer*, within *tol* px on every edge."""
    return (
        inner[0] >= outer[0] - tol
        and inner[1] >= outer[1] - tol
        and inner[0] + inner[2] <= outer[0] + outer[2] + tol
        and inner[1] + inner[3] <= outer[1] + outer[3] + tol
    )


def _is_deliberate_overlay(box_a: dict, rect_a, box_b: dict, rect_b) -> bool:
    """An ignoreclick=1 box inside the other's stored rect is an overlay
    readout (add_overlay_readout's recipe), never a warning."""
    if rect_a is None or rect_b is None:
        return False
    if box_a.get("ignoreclick") == 1 and _inside(rect_a, rect_b, _OVERLAY_TOLERANCE):
        return True
    if box_b.get("ignoreclick") == 1 and _inside(rect_b, rect_a, _OVERLAY_TOLERANCE):
        return True
    return False


def _check_overlapping_boxes(
    box_list: list[dict], *, max_saved: bool = False,
) -> list[CriticResult]:
    """Detect overlapping boxes (O(n^2) sweep, excluding decorative elements).

    Compares ``sizing.rendered_rect`` rects (a message box covers
    ``len*8+25`` px unless *max_saved*; Q27 / F5) with COLLISION_PAD.
    Skips comment and panel boxes since they are background elements
    that intentionally overlap content, boxes with an invalid rect, and
    deliberate overlays (an ``ignoreclick`` box inside the other's stored
    rect, as add_overlay_readout builds them).
    """
    results: list[CriticResult] = []

    # Filter to non-decorative boxes with a valid rect
    checked = []
    for b in box_list:
        if not isinstance(b, dict) or walk.box_maxclass(b) in _DECORATIVE_MAXCLASSES:
            continue
        rect = rendered_rect(b, max_saved=max_saved)
        if rect is None:
            continue
        checked.append((b, rect, _stored_rect(b)))

    for i in range(len(checked)):
        box_a, rect_a, stored_a = checked[i]
        for j in range(i + 1, len(checked)):
            box_b, rect_b, stored_b = checked[j]
            if not _rects_overlap(rect_a, rect_b, COLLISION_PAD):
                continue
            if _is_deliberate_overlay(box_a, stored_a, box_b, stored_b):
                continue
            id_a = box_a.get("id", "?")
            id_b = box_b.get("id", "?")
            label_a = _box_label(box_a)
            label_b = _box_label(box_b)
            results.append(CriticResult(
                "warning",
                f"Overlapping boxes: '{label_a}' ({id_a}) and "
                f"'{label_b}' ({id_b}) patching_rects overlap "
                f"(within {COLLISION_PAD}px padding)",
                "Adjust box positions to maintain at least "
                f"{COLLISION_PAD}px clearance between objects",
            ))

    return results


# ---------------------------------------------------------------------------
# Check 2: Missing cable midpoints
# ---------------------------------------------------------------------------

def _check_missing_midpoints(
    box_lookup: dict[str, dict],
    edges: list,
) -> list[CriticResult]:
    """Detect cables that need midpoints but don't have them.

    Checks two patterns:
    1. Horizontal offset > HORIZONTAL_THRESHOLD without midpoints
    2. Upward flow > UPWARD_BUS_THRESHOLD without midpoints
    """
    results: list[CriticResult] = []

    for edge in edges:
        midpoints = edge.line.get("midpoints", [])

        # Skip if midpoints already present
        if midpoints:
            continue

        src_id, src_outlet = edge.src, edge.outlet
        dst_id, dst_inlet = edge.dst, edge.inlet

        src_box = box_lookup.get(src_id)
        dst_box = box_lookup.get(dst_id)
        if not src_box or not dst_box:
            continue

        src_rect = src_box.get("patching_rect")
        dst_rect = dst_box.get("patching_rect")
        if not src_rect or not dst_rect or len(src_rect) < 4 or len(dst_rect) < 4:
            continue

        # Compute outlet/inlet positions
        src_ox = _outlet_x(src_box, src_outlet)
        src_oy = src_rect[1] + src_rect[3]  # bottom of source box
        dst_ix = _inlet_x(dst_box, dst_inlet)
        dst_iy = dst_rect[1]  # top of destination box

        hdist = abs(src_ox - dst_ix)
        vdist = src_oy - dst_iy  # positive means upward flow

        # Check horizontal offset
        if hdist > HORIZONTAL_THRESHOLD and vdist <= 0:
            results.append(CriticResult(
                "warning",
                f"Missing midpoints: cable {src_id}[{src_outlet}] -> "
                f"{dst_id}[{dst_inlet}] has {hdist:.0f}px horizontal "
                f"offset without segmented routing",
                "Add midpoints for clean L-shaped cable routing",
            ))
        # Check upward flow
        elif vdist > UPWARD_BUS_THRESHOLD:
            results.append(CriticResult(
                "warning",
                f"Missing midpoints: upward cable {src_id}[{src_outlet}] -> "
                f"{dst_id}[{dst_inlet}] flows {vdist:.0f}px upward "
                f"without bus routing midpoints",
                "Add bus routing midpoints for upward-flowing cables",
            ))

    return results


# ---------------------------------------------------------------------------
# Check 3: Out-of-bounds placement
# ---------------------------------------------------------------------------

def _check_out_of_bounds(box_list: list[dict]) -> list[CriticResult]:
    """Detect boxes placed outside the visible canvas (negative coordinates)."""
    results: list[CriticResult] = []

    for box in box_list:
        rect = _stored_rect(box) if isinstance(box, dict) else None
        if rect is None:
            continue

        x, y = rect[0], rect[1]
        if x < 0 or y < 0:
            box_id = box.get("id", "?")
            label = _box_label(box)
            results.append(CriticResult(
                "warning",
                f"Out-of-bounds placement: '{label}' ({box_id}) at "
                f"position ({x:.1f}, {y:.1f}) is outside the visible canvas",
                "Move the object to a position with x >= 0 and y >= 0",
            ))

    return results


# ---------------------------------------------------------------------------
# Check 5: Presentation coverage
# ---------------------------------------------------------------------------

# Interactive param-entry widgets that belong in presentation mode when the
# patch uses it. Monitoring/level objects (gain~, meter~, scope~) and comments
# are deliberately excluded: they are often patching-side by design (e.g. a
# slaved stereo fader) and would produce persistent false positives.
_INTERACTIVE_MAXCLASSES = frozenset({
    "flonum", "number", "umenu", "toggle", "textedit", "kslider",
    "dial", "slider", "multislider", "rslider", "incdec", "tab",
    "pictslider", "matrixctrl", "textbutton",
    "live.dial", "live.slider", "live.numbox", "live.menu",
    "live.toggle", "live.tab", "live.text", "live.button",
})


def _check_presentation_coverage(box_list: list[dict]) -> list[CriticResult]:
    """Flag interactive controls missing from presentation mode.

    Only active when the patch uses presentation mode at all (at least one
    box has presentation=1). Every interactive param widget added by an
    edit must either join the presentation layout or be a deliberate,
    documented exclusion -- silent omission is the recurring failure this
    check exists to catch.
    """
    if not any(b.get("presentation") for b in box_list):
        return []  # patch does not use presentation mode

    results: list[CriticResult] = []
    for box in box_list:
        if walk.box_maxclass(box) not in _INTERACTIVE_MAXCLASSES:
            continue
        if box.get("presentation"):
            continue
        box_id = box.get("id", "?")
        label = _box_label(box)
        results.append(CriticResult(
            "warning",
            f"Presentation coverage: interactive control '{label}' "
            f"({box_id}) is not in presentation mode, but this patch "
            "uses presentation mode",
            "Add it via Patcher.add_to_presentation(box, rect) with its "
            "label comment, or record a deliberate exclusion in context.md",
        ))
    return results


# ---------------------------------------------------------------------------
# Check 4: Low-contrast text
# ---------------------------------------------------------------------------


def _resolve_patcher_bg(patcher_props: dict) -> list[float]:
    """Patcher background, preferring the key MAX honors in locked mode.

    Delegates to :func:`src.maxpat.aesthetics.resolve_patcher_background`
    (the generator's helper), so a patcher with no bg key reads as the
    Max 9 theme canvas 0.235 in both (Q26 / E7).
    """
    from src.maxpat.aesthetics import resolve_patcher_background

    return resolve_patcher_background(patcher_props)


def _check_text_contrast(box_list: list[dict], patcher_props: dict) -> list[CriticResult]:
    """Detect text boxes that fail WCAG contrast against their REAL background.

    Evaluates the EFFECTIVE background -- the box's own bgcolor, else the panel
    beneath it in whichever coordinate space the text is displayed in, else the
    patcher background -- rather than comparing against the palette canvas
    constant. The resolution logic is imported from src.maxpat.aesthetics so
    the critic and the generator cannot drift apart: one helper each builds
    the panel layers (:func:`build_panel_layers`, topmost visible panel
    first) and the patcher background. A missing or invalid textcolor is
    the Max 9 theme text color MAX_THEME_TEXT (0.85); an untinted
    object / message / umenu box reads against the theme box fill 0.172
    (Q26 / E7).

    Severity:
      - ``warning`` when the background is KNOWN and the ratio falls short.
      - ``note`` when the background had to be ASSUMED (panel with no color
        encoding), since the shortfall may not be real.
      - ``note`` for the D-1 case where presentation was chosen and patching
        mode is the compromised space.
    """
    from src.maxpat.aesthetics import (
        build_panel_layers,
        contrast_ratio,
        is_text_contrast_target,
        is_valid_color,
        resolve_effective_background,
    )
    from src.maxpat.defaults import MAX_THEME_TEXT, MIN_CONTRAST_RATIO

    results: list[CriticResult] = []
    patcher_bg = _resolve_patcher_bg(patcher_props)

    panels = [b for b in box_list if b.get("maxclass") == "panel"]
    patching_layers, presentation_layers = build_panel_layers(
        (b, b.get("patching_rect"), bool(b.get("presentation")), b.get("presentation_rect"))
        for b in panels
    )

    for box in box_list:
        if box.get("maxclass") == "panel":
            continue
        if not is_text_contrast_target(walk.box_maxclass(box) or None, box):
            continue

        textcolor = box.get("textcolor")
        if not is_valid_color(textcolor):
            textcolor = list(MAX_THEME_TEXT)

        resolution = resolve_effective_background(
            box,
            box.get("patching_rect"),
            bool(box.get("presentation")),
            box.get("presentation_rect"),
            patching_layers,
            presentation_layers,
            patcher_bg,
            maxclass=walk.box_maxclass(box) or None,
        )

        text = walk.box_text(box)
        label = text[:40] if text else "(empty)"
        ratio = contrast_ratio(textcolor, resolution.color)
        space = {
            "own": "own background",
            "presentation": "presentation-mode background",
            "patching": "patching-mode background",
        }[resolution.space]

        if ratio < MIN_CONTRAST_RATIO:
            if resolution.assumed:
                results.append(CriticResult(
                    "note",
                    f"Low contrast text: '{label}' scores {ratio:.2f}:1 against "
                    f"its {space}, below the WCAG AA minimum of "
                    f"{MIN_CONTRAST_RATIO}:1 -- but that background was ASSUMED "
                    "(the panel beneath it carries no color encoding), so the "
                    "shortfall may not be real",
                    "Give the panel an explicit bgcolor/bgfillcolor, then run "
                    "ensure_text_contrast() (new patches) or "
                    "repair_text_contrast(patcher) (existing patches)",
                ))
            else:
                results.append(CriticResult(
                    "warning",
                    f"Low contrast text: '{label}' scores {ratio:.2f}:1 against "
                    f"its {space}, below the WCAG AA minimum of "
                    f"{MIN_CONTRAST_RATIO}:1",
                    "Set textcolor via ensure_text_contrast() in the styling "
                    "pipeline, or repair_text_contrast(patcher) on an existing "
                    "patch",
                ))
            continue

        # D-1: presentation won, so patching mode may be the compromised space.
        if resolution.space == "presentation" and resolution.patching_color is not None:
            patch_ratio = contrast_ratio(textcolor, resolution.patching_color)
            if patch_ratio < MIN_CONTRAST_RATIO:
                results.append(CriticResult(
                    "note",
                    f"Presentation/patching contrast trade-off: '{label}' reads "
                    f"at {ratio:.2f}:1 in presentation but only "
                    f"{patch_ratio:.2f}:1 in patching mode. Presentation was "
                    "chosen because it is the user-facing surface (D-1)",
                    "No action needed unless this label is primarily read while "
                    "editing; if so, move it onto a panel in patching space too",
                ))

    return results
