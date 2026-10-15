# UI Presets Reference

Standardized control appearance derived from rhythmic-sampler dial patterns. All agents generating UI controls should follow these presets for visual consistency.

## Dial Preset

Exact JSON attributes for dial objects:

```json
{
  "box": {
    "maxclass": "dial",
    "numinlets": 1,
    "numoutlets": 1,
    "outlettype": [""],
    "parameter_enable": 0,
    "patching_rect": [X, Y, 40.0, 40.0],
    "presentation": 1,
    "presentation_rect": [X, Y, 55.0, 55.0],
    "varname": "descriptive_name_dial"
  }
}
```

**Key values:**
- Patching mode size: **40x40px**
- Presentation mode size: **55x55px**
- `parameter_enable`: 0 (no automation/parameter system)
- Always include `varname` with descriptive `_dial` suffix
- Always set both `presentation: 1` and explicit `presentation_rect`
- Output range: 0-127 (default dial behavior)

## Scale Chain Presets

Standard mappings from dial output (0-127) to parameter ranges:

| Parameter Type | Scale Text | Output Range | Example Use |
|----------------|-----------|--------------|-------------|
| Frequency (Hz) | `scale 0 127 20. 20000.` | 20-20000 | Filter cutoff |
| Normalized 0-1 | `scale 0 127 0. 1.` | 0.0-1.0 | Volume, resonance, mix |
| Gain (dB) | `scale 0 127 -70. 6.` | -70 to +6 | Level meter range |
| Time (ms) | `scale 0 127 1. 5000.` | 1-5000 | Delay, attack, release |
| Pitch (semitones) | `expr pow(2., $f1 / 12.)` | Ratio | Pitch shift |
| Percentage | `scale 0 127 0. 100.` | 0-100 | Dry/wet, feedback |
| Detune (cents) | `scale 0 127 -100. 100.` | -100 to +100 | Fine tuning |

**Pattern:** `dial` (0-127) -> `scale 0 127 min max` -> parameter inlet

## Number Display Preset

Readout box for showing mapped parameter value:

```json
{
  "box": {
    "maxclass": "number",
    "numinlets": 1,
    "numoutlets": 2,
    "outlettype": ["", "bang"],
    "patching_rect": [X, Y, 50.0, 22.0],
    "presentation": 1,
    "presentation_rect": [X, Y, 100.0, 22.0]
  }
}
```

- Patching: **50x22px**
- Presentation: **100x22px**
- Connected AFTER the scale object (shows mapped value, not raw 0-127)
- Always set `presentation: 1`

## Presentation Layout Grid

Consistent dial layout using 60px horizontal column spacing:

| Column | X Position |
|--------|-----------|
| 1 | 5 |
| 2 | 65 |
| 3 | 125 |
| 4 | 185 |
| 5 | 245 |
| 6 | 305 |

**Vertical spacing:** 80px per row (55px dial + 25px gap for label below)

**Labels:** Comment objects placed below each dial with parameter name.

## Toggle/Button Presets

### Toggle
```json
{
  "box": {
    "maxclass": "toggle",
    "numinlets": 1,
    "numoutlets": 1,
    "outlettype": ["int"],
    "parameter_enable": 0,
    "patching_rect": [X, Y, 20.0, 20.0],
    "presentation": 1,
    "presentation_rect": [X, Y, 30.0, 30.0]
  }
}
```

### Button
```json
{
  "box": {
    "maxclass": "button",
    "numinlets": 1,
    "numoutlets": 1,
    "outlettype": ["bang"],
    "parameter_enable": 0,
    "patching_rect": [X, Y, 20.0, 20.0],
    "presentation": 1,
    "presentation_rect": [X, Y, 30.0, 30.0]
  }
}
```

## Complete Dial Chain Example

A typical dial-to-parameter chain for filter cutoff:

```
dial (40x40, presentation 55x55, varname "cutoff_dial")
  |
scale 0 127 20. 20000.
  |
t f f                     (trigger: right outlet fires first, Rule #3)
  |   \
  |    +---> number (50x22, presentation 100x22)      [right outlet]
  |
  +---> gen~ param message: "cutoff $1"              [left outlet]
```

## Max 9 Theme Defaults

What MAX 9 draws when a box or patcher does not set its own color. Values come from the `styledefaults` of `/Applications/Max.app/Contents/Resources/C74/interfaces/themes/default.maxtheme` (Max 9.2.0); all are grays (r = g = b, alpha 1).

| Surface | `styledefaults` key(s) | Value |
|---|---|---|
| Text | `textcolor` | 0.85 |
| Patcher canvas (editing and locked) | `editing_bgcolor`, `locked_bgcolor` | 0.235 |
| Box fill | `bgfillcolor_color`, `bgfillcolor_color1`, `bgfillcolor_color2` | 0.172 |
| Window background | `bgcolor` | 0.125 |

- A box with no `textcolor` renders its text at the theme text color, 0.85 (light gray), not black.
- The contrast critic (`layout_critic.py`) and `aesthetics.py` still assume the legacy defaults (black text when `textcolor` is missing, a 0.333 canvas) until Q26 (review E7) makes them theme-aware. So before recoloring a box that has no `textcolor` because of a "Low contrast text" warning, check the warning against these values: 0.85 text on a 0.235 canvas is readable.

## Text Contrast Resolution

The full algorithm behind CLAUDE.md Rule #4 "Text Contrast: Resolve Against the Displayed Surface". The contrast code still assumes the legacy defaults described in "Max 9 Theme Defaults" above until Q26.

Text color is NEVER chosen against the editing background alone. Resolve it against the **effective background in whichever coordinate space the text is displayed in**, and judge it by WCAG contrast ratio (minimum 4.5:1, `MIN_CONTRAST_RATIO` in `defaults.py`), not by a `luminance > 0.5` flip.

Precedence when resolving the effective background:

1. **A box's own `bgcolor` wins over any panel beneath it.** A box that paints its own background IS its own background. `add_section_header` pairs a light `header_bgcolor` with its text; the reader sees that pairing, not the dark canvas behind it.
2. **Presentation coordinates, when the box is in presentation** — the box's `presentation_rect` center against the `presentation_rect` of panels that are themselves in presentation. Presentation is the user-facing surface, so it decides on conflict; the layout critic emits a `note` naming the box when patching mode is the compromised space.
3. **Patching coordinates** — `patching_rect` center against panels' `patching_rect`s.
4. **Patcher background** as fallback.

Panels encode their fill three different ways and all three must be read: `bgfillcolor` dict (`color1`, else `color`), a flat top-level `grad1`, or `bgcolor`. A panel with none of them is genuinely indeterminate — MAX ships no discoverable default — so treat it as *assumed* and pick the text color that maximizes the MINIMUM contrast across the plausible surfaces rather than betting on a guess.

Use `ensure_text_contrast(patcher)` on new patches (it runs automatically via `apply_auto_styling`) and the explicitly-called `repair_text_contrast(patcher)` on existing ones. Contrast is NOT recomputed on the edit path — `apply_auto_styling` runs only when `finalize_patch(is_new=True)` — so an edited patch keeps whatever text colors it already had unless you call the repair helper.
