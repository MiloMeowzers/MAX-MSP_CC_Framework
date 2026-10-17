"""Maxclass resolver: UI object set and resolve_maxclass function.

In .maxpat files, UI objects use their own name as maxclass (e.g., "toggle"),
while non-UI objects use "newobj" with the object name in the "text" field.

The UI_MAXCLASSES set is derived from 02-RESEARCH.md Pattern 7, verified against
MAX SDK scripting docs and py2max. Entries are also admitted on committed-patch
evidence: a patch that MAX itself wrote or re-saved (discriminated by a non-zero
``patcher.appversion.revision`` -- this repo's generator hardcodes ``0``, see
defaults.py) is authoritative for whether a box carries its own name as maxclass.
Entries admitted that way name their confirming patch in an inline comment.

Non-UI ``live.*`` objects (live.thisdevice, live.path, live.object, ...) and
``p``/``patcher`` are deliberately absent on bundle evidence: Max 9.2 saves
each of them only as a newobj box with the name in ``text``, never with its
own maxclass (review C4, fix-plan Q13).

``python3 tools/sync_max_bundle.py`` (section ``ui_maxclasses``) regenerates
the set from a survey of every box in the bundle's .maxpat/.maxhelp files for
review; the set itself is still edited by hand.

``ui_control_names(db)`` derives the UI-control set from the DB; the three
purpose subsets (LAYOUT_BAND_CONTROLS, PRESENTATION_CONTROLS,
PARAMETER_LIST_CONTROLS) live beside it (fix-plan Q33 / review S12).
"""

import functools

# All UI maxclass names that use their own name (NOT "newobj") in .maxpat files.
# Verified from 02-RESEARCH.md Pattern 7 + MAX SDK scripting docs.
UI_MAXCLASSES: frozenset[str] = frozenset({
    # Text/display UI
    "comment", "message",
    # Number UI
    "number", "flonum",
    # Toggle/button UI
    "toggle", "button",
    # Slider/dial UI
    "slider", "dial", "rslider", "multislider",
    # Keyboard UI
    "kslider", "nslider",
    # Panel/display
    "panel", "led", "radiogroup",
    # Text interaction UI
    "textbutton", "tab", "umenu", "textedit",
    # Specialized UI
    "pictctrl", "pictslider", "incdec",
    "swatch", "colorpicker", "chooser", "listbox",
    "attrui", "preset", "matrixctrl", "nodes", "function",
    # Special display
    "jsui", "fpic", "lcd", "hint",
    "dropfile", "ubutton", "playbar",
    # Patcher structure
    "inlet", "outlet", "bpatcher",
    # MSP UI (only objects that use their own name as maxclass in .maxpat)
    "meter~", "levelmeter~", "spectroscope~", "scope~",
    "number~", "gain~", "ezdac~", "ezadc~",
    "filtergraph~", "waveform~",
    # Jitter UI (MAX re-saves these with their own maxclass; terrain-synth v0.3-v0.4)
    "jit.pwindow", "jit.cellblock",
    # Max for Live UI (visual widgets)
    "live.dial", "live.slider", "live.numbox",
    "live.toggle", "live.button", "live.text",
    "live.menu", "live.tab", "live.meter~", "live.gain~",
    "live.scope~",
    "live.arrows", "live.comment",
    "live.drop", "live.grid", "live.line", "live.step",
    # Deliberately absent (review C4, Q13): the 14 non-UI live.* objects
    # (live.observer, live.thisdevice, live.path, live.object, live.map,
    # live.routing, live.push, live.miditool.in, live.miditool.out,
    # live.remote~, live.param~, live.modulate~, live.banks, live.colors) and
    # p/patcher. Max 9.2 saves them only as newobj with the name in `text`
    # (live.thisdevice 107 boxes, live.path 112, live.object 99, patcher 126
    # + p 6,901) and never as their own maxclass in 3,139 bundle files.
    # A subpatcher is built with Patcher.add_subpatcher, not add_box("p").
    # Embedded code editors (not visual widgets, but MAX writes them with
    # their own maxclass and no `text` field -- confirmed in kicksynth.maxpat
    # at 02c9917 and terrain-synth.maxpat at 55757e0, both appversion 9.1.5;
    # their `in 1`/`out 1` siblings in the same gen~ patcher stay newobj). SF-03.
    "codebox",
    # Specialty / package UI widgets
    "playlist~",      # Max-bundled clip-player UI widget
    "dict.view",      # Max-bundled dict viewer UI widget
    "dada.bounce",    # dada package physics-balls UI widget
    "bach.roll",      # bach package notation-roll UI widget
    # Bundle-verified UI widgets (review C5, Q13): Max 9.2.0 saves each with
    # its own maxclass and never as newobj; `python3 tools/sync_max_bundle.py`
    # (section ui_maxclasses) re-derives the evidence. markup and progress
    # have no DB entry, so add_box refuses them (Rule #1).
    "jit.fpsgui", "jit.playlist", "jit.pworld", "plot~",
    "mc.ezdac~", "mc.live.gain~", "markup", "v8ui", "v8.codebox",
    "live.adsrui", "mc.number~", "itable", "multirange", "gridmeter~",
    "node.codebox", "text.codebox", "zplane~", "progress",
})


def resolve_maxclass(object_name: str) -> str:
    """Resolve the .maxpat maxclass field for a given object name.

    UI objects use their own name as maxclass.
    Non-UI objects use "newobj" with the object name in the "text" field.

    Args:
        object_name: The MAX object name (e.g., "cycle~", "toggle", "pack").

    Returns:
        The maxclass string for use in .maxpat JSON.
    """
    if object_name in UI_MAXCLASSES:
        return object_name
    return "newobj"


def is_ui_object(object_name: str) -> bool:
    """Check whether an object is a UI object.

    Args:
        object_name: The MAX object name.

    Returns:
        True if the object uses its own name as maxclass in .maxpat files.
    """
    return object_name in UI_MAXCLASSES


@functools.lru_cache(maxsize=1)
def _default_db():
    """One process-wide ObjectDatabase for ``db=None`` callers (cached)."""
    from src.maxpat.db_lookup import ObjectDatabase

    return ObjectDatabase()


def ui_control_names(db=None) -> frozenset[str]:
    """UI controls: UI_MAXCLASSES members the DB marks as parameters.

    A member counts when ``db.attributes(name)`` has ``parameter_enable`` or
    ``parameter_mappable`` (47 names under the repo DB). This is the DB
    authority the three purpose subsets below are pinned against (fix-plan
    Q33 / review S12); no consumer uses it directly yet. ``db=None`` uses
    one process-wide cached ObjectDatabase.
    """
    if db is None:
        db = _default_db()
    names = set()
    for name in UI_MAXCLASSES:
        attrs = db.attributes(name)
        if attrs and ("parameter_enable" in attrs or "parameter_mappable" in attrs):
            names.add(name)
    return frozenset(names)


# Purpose subsets of ui_control_names(). They differ on purpose: unifying
# them changes layout, critic and analyze() output, so it is a recorded user
# decision (Q33 SUMMARY, PD-6), not a refactor. A test pins each as a subset
# of ui_control_names(db) and equal to its pre-Q33 members.

# apply_layout: controls placed in a band above the object they feed.
# Matched by box name.
LAYOUT_BAND_CONTROLS: frozenset[str] = frozenset({
    "toggle", "slider", "dial", "number", "flonum",
    "rslider", "button", "multislider", "kslider",
    "nslider", "led", "radiogroup", "umenu",
    "live.dial", "live.slider", "live.numbox",
    "live.toggle", "live.button",
})

# Layout critic presentation coverage: interactive param-entry widgets that
# belong in presentation mode when the patch uses it. Monitoring/level
# objects (gain~, meter~, scope~) and comments are deliberately excluded:
# they are often patching-side by design (e.g. a slaved stereo fader) and
# would produce persistent false positives. Matched by maxclass.
PRESENTATION_CONTROLS: frozenset[str] = frozenset({
    "flonum", "number", "umenu", "toggle", "textedit", "kslider",
    "dial", "slider", "multislider", "rslider", "incdec", "tab",
    "pictslider", "matrixctrl", "textbutton",
    "live.dial", "live.slider", "live.numbox", "live.menu",
    "live.toggle", "live.tab", "live.text", "live.button",
})

# Patcher.analyze()'s parameter list; includes gain~ / live.gain~.
# Matched by maxclass.
PARAMETER_LIST_CONTROLS: frozenset[str] = frozenset({
    "slider", "dial", "rslider", "multislider",
    "number", "flonum", "toggle", "button",
    "kslider", "nslider", "umenu", "textbutton",
    "tab", "gain~", "live.dial", "live.slider",
    "live.numbox", "live.toggle", "live.button",
    "live.menu", "live.tab", "live.gain~",
})
