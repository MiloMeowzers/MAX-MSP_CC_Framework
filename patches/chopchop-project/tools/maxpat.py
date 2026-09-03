"""maxpat -- minimal .maxpat builder for ChopChop scratch test patchers.

NOT for building the device. This exists only to hand-write throwaway diagnostic
patchers per the `chopchop-max-testing` skill (verify one karma~/Max behaviour,
click through numbered steps, read the result, discard). It is deliberately tiny
and makes no attempt at validation -- the point of a test patcher is to see what
Max actually does.

Conventions baked in (learned the hard way, per the skill):
  * buffer~ objects are emitted first in the boxes array (Max instantiates in
    file order; a karma~ before its buffer errors)
  * patcher dict has "locked": 1
  * a DSP sink is your job -- add `ezdac~` (through `*~ 0.` for silence) and tell
    the user to click it first
  * karma~ stereo == `karma~ <buf> 2`  -> 3 inlets / 3 outlets; feed a `sig~ 1`
    into its speed (rightmost) inlet or it sits at zero
  * use plain names, never `---` scoped names, in a standalone patcher
"""
from __future__ import annotations

import json
from pathlib import Path


class Patch:
    def __init__(self, title="scratch", grid=(150, 90), origin=(40, 40)):
        self._boxes = []
        self._bufs = []
        self._lines = []
        self._n = 0
        self.gx, self.gy = grid
        self.ox, self.oy = origin
        self.title = title

    # -- box adders ------------------------------------------------------------
    def _add(self, d, is_buffer=False):
        self._n += 1
        d.setdefault("id", f"obj-{self._n}")
        d.setdefault("patching_rect", [
            self.ox + (len(self._boxes) % 6) * self.gx,
            self.oy + (len(self._boxes) // 6) * self.gy,
            120.0, 22.0,
        ])
        (self._bufs if is_buffer else self._boxes).append({"box": d})
        return d["id"]

    def obj(self, text, at=None, **attrs):
        d = {"maxclass": "newobj", "text": text,
             "numinlets": attrs.pop("numinlets", 2),
             "numoutlets": attrs.pop("numoutlets", 1),
             "outlettype": attrs.pop("outlettype", [""])}
        if at:
            d["patching_rect"] = [float(at[0]), float(at[1]), float(at[2] if len(at) > 2 else 120), 22.0]
        d.update(attrs)
        return self._add(d, is_buffer=text.split()[0] == "buffer~")

    def msg(self, text, at=None, **attrs):
        d = {"maxclass": "message", "text": text, "numinlets": 2, "numoutlets": 1,
             "outlettype": [""]}
        if at:
            d["patching_rect"] = [float(at[0]), float(at[1]), float(at[2] if len(at) > 2 else 120), 22.0]
        d.update(attrs)
        return self._add(d)

    def comment(self, text, at=None, w=200):
        d = {"maxclass": "comment", "text": text, "numinlets": 1, "numoutlets": 0}
        if at:
            d["patching_rect"] = [float(at[0]), float(at[1]), float(w), 20.0]
        return self._add(d)

    def ui(self, maxclass, at=None, ins=1, outs=1, **attrs):
        d = {"maxclass": maxclass, "numinlets": ins, "numoutlets": outs}
        if at:
            d["patching_rect"] = [float(at[0]), float(at[1]),
                                  float(at[2] if len(at) > 2 else 45),
                                  float(at[3] if len(at) > 3 else 45)]
        d.update(attrs)
        return self._add(d)

    # -- wiring --------------------------------------------------------------
    def connect(self, src, so, dst, di):
        self._lines.append({"patchline": {
            "source": [src, int(so)], "destination": [dst, int(di)],
        }})

    # -- output -----------------------------------------------------------
    def to_dict(self):
        return {"patcher": {
            "fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box",
            "rect": [80.0, 80.0, 1200.0, 800.0],
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
            "locked": 1,
            "boxes": self._bufs + self._boxes,   # buffers first
            "lines": self._lines,
        }}

    def save(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2))
        return p
