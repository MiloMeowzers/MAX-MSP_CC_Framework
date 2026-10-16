"""MAX 9 default patcher properties, font constants, spacing constants.

All values match the MAX 9 .maxpat JSON structure verified in 02-RESEARCH.md Pattern 1.
"""

from dataclasses import dataclass

# Font constants (MAX 9 defaults)
FONT_NAME = "Arial"
FONT_SIZE = 12.0
CHAR_WIDTH = 7.0       # Approximate pixels per character at 12pt Arial
PADDING = 16.0          # Left + right padding inside a box
MIN_BOX_WIDTH = 40.0    # Minimum box width for very short objects
DEFAULT_HEIGHT = 22.0   # Standard text box height (newobj, message)

# Rendered-geometry constants (12 pt; used by sizing.rendered_rect, Q27 / F5).
# Message boxes render wider than their stored width (CLAUDE.md Rule #4):
# longest line * MESSAGE_CHAR_WIDTH + MESSAGE_CHROME.
MESSAGE_CHAR_WIDTH = 8.0
MESSAGE_CHROME = 25.0
# Comments (measured in Max 9.2): ~5.6 px per char plus padding; a paragraph
# wraps at the box width only once its text is >= 1.6x that width,
# otherwise it overflows as one line.
COMMENT_CHAR_WIDTH = 5.6
COMMENT_TEXT_PAD = 10.0
COMMENT_WRAP_RATIO = 1.6
COMMENT_LINE_HEIGHT = 14.0
COMMENT_BASE_HEIGHT = 6.0

# Global auto-layout limits (Q27 / F5): rows, component bands and the
# disconnected column wrap so content stays within LAYOUT_MAX_WIDTH px of
# the layout origin; apply_layout refuses patchers with more boxes than
# LAYOUT_MAX_BOXES (or MAX-saved ones) unless forced.
LAYOUT_MAX_WIDTH = 1600.0
LAYOUT_MAX_BOXES = 120

# Layout spacing constants
V_SPACING = 20          # Vertical gap between rows (~16-20px matches real MAX patches)
H_GUTTER = 15           # Horizontal gap between objects in a row

# Multislider labeled parameter bank layout constants
MS_BAR_HEIGHT = 24.0       # Height per bar for labeled multislider banks
MS_LABEL_FONTSIZE = 10.0   # Font size for multislider row labels
MS_LABEL_HEIGHT = 18.0     # Comment box height for multislider row labels
MS_LABEL_WIDTH = 85.0      # Comment box width for multislider row labels
MS_GAP = 8.0               # Horizontal gap between adjacent multisliders in a bank

# Midpoint generation thresholds
HORIZONTAL_THRESHOLD = 20.0   # Min horizontal offset to trigger midpoint generation
UPWARD_BUS_THRESHOLD = 60.0   # Min upward distance to use right-edge bus routing
BUS_MARGIN = 30.0             # Gap between rightmost object and bus start X
BUS_SPACING = 8.0             # Spacing between parallel bus cables
PATCHER_PADDING = 40.0        # Padding around content for auto-sized patcher rect


@dataclass
class LayoutOptions:
    """Configurable layout parameters for patch generation.

    Default values match existing module-level constants for backward
    compatibility. Pass to apply_layout() to customize spacing and alignment.
    """
    v_spacing: float = 20.0
    h_gutter: float = 15.0
    patcher_padding: float = 40.0
    grid_size: float = 15.0
    grid_snap: bool = True
    inlet_align: bool = True
    comment_gap: float = 10.0
    max_width: float = LAYOUT_MAX_WIDTH


# Subpatcher default window size
SUBPATCHER_RECT = [100.0, 100.0, 400.0, 300.0]

# Gen~ inner patcher background color (light gray, matches MAX default)
GEN_PATCHER_BGCOLOR = [0.9, 0.9, 0.9, 1.0]

# Complete MAX 9 patcher wrapper defaults (from 02-RESEARCH.md Pattern 1)
DEFAULT_PATCHER_PROPS = {
    "fileversion": 1,
    "appversion": {
        "major": 9,
        "minor": 0,
        "revision": 0,
        "architecture": "x64",
        "modernui": 1,
    },
    "classnamespace": "box",
    "rect": [85.0, 104.0, 640.0, 480.0],
    "bglocked": 0,
    "openinpresentation": 0,
    "default_fontsize": 12.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 1,
    "gridsize": [15.0, 15.0],
    "gridsnaponopen": 1,
    "objectsnaponopen": 1,
    "statusbarvisible": 2,
    "toolbarvisible": 1,
    "lefttoolbarpinned": 0,
    "toptoolbarpinned": 0,
    "righttoolbarpinned": 0,
    "bottomtoolbarpinned": 0,
    "toolbars_unpinned_last_save": 0,
    "tallnewobj": 0,
    "boxanimatetime": 200,
    "enablehscroll": 1,
    "enablevscroll": 1,
    "devicewidth": 0.0,
    "description": "",
    "digest": "",
    "tags": "",
    "style": "",
    "subpatcher_template": "",
    "assistshowspatchername": 0,
    "boxes": [],
    "lines": [],
    "dependency_cache": [],
    "autosave": 0,
}

# Fontface constants (bitmask encoding used in .maxpat JSON)
FONTFACE_REGULAR = 0
FONTFACE_BOLD = 1
FONTFACE_ITALIC = 2
FONTFACE_BOLD_ITALIC = 3

# Bubbleside constants (comment box bubble arrow direction)
BUBBLE_LEFT = 0     # Arrow points left, bubble on right
BUBBLE_TOP = 1      # Arrow points up, bubble below (default)
BUBBLE_RIGHT = 2    # Arrow points right, bubble on left
BUBBLE_BOTTOM = 3   # Arrow points down, bubble above

# Semantic color palette -- all RGBA values in [0.0, 1.0] range.
# Cool/neutral temperature: blues, grays, slate tones matching MAX 9 UI.
AESTHETIC_PALETTE = {
    # Comment tiers
    "header_color": [0.20, 0.25, 0.42, 1.0],         # deep slate blue text
    "header_bgcolor": [0.88, 0.90, 0.95, 1.0],        # light blue-gray background
    "subsection_color": [0.30, 0.30, 0.35, 1.0],      # dark gray
    "annotation_color": [0.55, 0.55, 0.60, 1.0],      # light gray
    "warning_color": [0.75, 0.22, 0.17, 1.0],         # muted red for warnings

    # Panel fills
    "panel_fill": [0.94, 0.94, 0.96, 1.0],            # very light cool gray
    "panel_gradient_end": [0.88, 0.89, 0.92, 1.0],    # slightly darker cool gray

    # Canvas
    "canvas_bg": [0.333, 0.333, 0.333, 1.0],           # standard MAX 9 dark grey

    # Step markers
    "step_marker_bg": [0.85, 0.65, 0.13, 1.0],        # amber/gold
    "step_marker_text": [1.0, 1.0, 1.0, 1.0],         # white

    # Object emphasis (when explicitly requested)
    "emphasis_loadbang": [0.85, 0.92, 0.85, 1.0],     # pale green
    "emphasis_dac": [0.92, 0.85, 0.85, 1.0],          # pale red
    "emphasis_processor": [0.85, 0.87, 0.95, 1.0],    # pale blue
}

# ---------------------------------------------------------------------------
# Text contrast constants
# ---------------------------------------------------------------------------
# Deliberately NOT members of AESTHETIC_PALETTE: the palette is the project's
# visual identity and is held fixed; these two are measurement thresholds.

# WCAG 2.1 AA minimum contrast ratio for normal-size body text
# (W3C WCAG 2.1, Success Criterion 1.4.3 "Contrast (Minimum)").
MIN_CONTRAST_RATIO = 4.5

# Assumed fill for a `panel` box that carries NO color encoding at all --
# no `bgcolor`, no `bgfillcolor`, no flat `grad1`.
#
# PROVENANCE / ASSUMPTION (finding F-3): MAX ships no discoverable default for
# this case. `/Applications/Max.app/Contents/Resources/C74/interfaces/
# maxcolors.json` has no `panel` entry, and `docs/refpages/max-ref/
# panel.maxref.xml` documents `bgcolor`/`bgfillcolor` without default values.
# Measuring MAX's own 2973 shipped panel boxes does not settle it either: the
# 2889 that DO carry a color skew dark (1177 pure black, 607 near-black), while
# 84 carry no color key at all, so no majority-usage inference is available for
# the uncolored case.
#
# The value below is therefore an explicit assumption, not a measured fact. It
# is made NON-LOAD-BEARING by design: `_get_panel_bgcolor()` reports the color
# as *assumed* rather than *found*, and callers then run the assumed background
# together with the canvas background through `best_text_color()`, which picks
# the candidate maximizing the MINIMUM contrast ratio across both. The layout
# critic likewise downgrades such findings from `warning` to `note`.
MAX_DEFAULT_PANEL_BG = [0.85, 0.85, 0.85, 1.0]

# Max 9 default-theme colors (Q26 / review E7). PROVENANCE: the `styledefaults`
# of /Applications/Max.app/Contents/Resources/C74/interfaces/themes/
# default.maxtheme in Max 9.2.0 -- `textcolor` (0.85), `editing_bgcolor` and
# `locked_bgcolor` (0.235), `bgfillcolor_color` / `bgfillcolor_color1` /
# `bgfillcolor_color2` (0.172). These are what MAX draws when a box or patcher
# sets no color of its own; the contrast critic and ensure_text_contrast read a
# missing textcolor, a patcher with no bg key and an untinted object / message /
# umenu box against them.
MAX_THEME_TEXT = [0.85, 0.85, 0.85, 1.0]
MAX_THEME_CANVAS_BG = [0.235, 0.235, 0.235, 1.0]
MAX_THEME_BOX_FILL = [0.172, 0.172, 0.172, 1.0]

# A fill whose alpha is below this is treated as transparent: the surface
# beneath it shows through (35 corpus flonums and 10 number boxes carry
# [0, 0, 0, 0]).
MIN_VISIBLE_FILL_ALPHA = 0.5
