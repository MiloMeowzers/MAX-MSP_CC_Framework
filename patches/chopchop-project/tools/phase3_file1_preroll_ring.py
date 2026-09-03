"""v6_184 -- Phase 3 file 1: the preroll capture ring + "full" LED.

Adds `p Preroll` (subpatcher at root) fed the device input (ingain_L/R):

  record~ ---thisBuffer 2 @loop 1   -- circular capture of the input
  runs ONLY while  ---prerollArm == 1  AND  ---hasContent == 0  (clean state)
  on start: `reset, 1` (write head to 0)          on stop: `0`
  ---size (LoopLength ms) drives a `delay`; after one full ring pass ->
    s ---prerollFull 1  (LED green).  LoopLength change -> reset the ring,
    restart the delay, s ---prerollFull 0.  ---hasContent -> 1 force-stops it.

Root: `record_arm_toggle` (obj-29, previously dead) -> `s ---prerollArm` and
promoted into the OVERDUB panel's right edge with an "ARM" label and a `led`
(`r ---prerollFull`) + "FULL" label beside it.

No behaviour change to normal operation: the ring only writes ---thisBuffer
while ---hasContent == 0 (karma A idle), and File 2 (the capture handoff) is
not built yet, so a normal Record still clears + records as before.

    python phase3_file1_preroll_ring.py   # -> ../generated/ChopChop_v6_184.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_183.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_184.amxd"
ORANGE = [1.0, 0.709803921568627, 0.196078431372549, 1.0]


def O(i, text, x, y, w=110, nin=2, nout=1, ot=None, extra=None):
    d = {"id": i, "maxclass": "newobj", "text": text, "numinlets": nin, "numoutlets": nout,
         "outlettype": ot if ot is not None else [""], "patching_rect": [float(x), float(y), float(w), 20.0]}
    if extra:
        d.update(extra)
    return {"box": d}


def M(i, text, x, y, w=90):
    return {"box": {"id": i, "maxclass": "message", "text": text, "numinlets": 2, "numoutlets": 1,
                    "outlettype": [""], "patching_rect": [float(x), float(y), float(w), 20.0]}}


def IN(i, x, y):
    return {"box": {"id": i, "maxclass": "inlet", "numinlets": 0, "numoutlets": 1,
                    "outlettype": ["signal"], "patching_rect": [float(x), float(y), 30.0, 30.0]}}


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def preroll_patcher():
    boxes = [
        IN("p_l", 20, 20), IN("p_r", 70, 20),
        O("pr_rec", "record~ ---thisBuffer 2 @loop 1", 20, 70, 210, nin=3, nout=1, ot=["signal"]),
        O("pr_arm", "r ---prerollArm", 300, 20, 110, nin=0, nout=1),
        O("pr_hc", "r ---hasContent", 300, 50, 110, nin=0, nout=1),
        O("pr_size", "r ---size", 300, 80, 90, nin=0, nout=1),
        O("pr_armf", "f", 300, 46 + 4, 30),
        O("pr_hcinv", "== 0", 430, 50, 40),
        O("pr_gate", "gate 1", 300, 110, 54, nin=2, nout=1),
        O("pr_run", "change", 300, 140, 54),
        O("pr_runsel", "sel 1 0", 300, 170, 54, nin=3, nout=3, ot=["bang", "bang", ""]),
        O("pr_hcsel", "sel 0 1", 430, 90, 54, nin=3, nout=3, ot=["bang", "bang", ""]),
        M("pr_start", "reset, 1", 300, 200, 70),
        M("pr_stop", "0", 380, 200, 26),
        O("pr_lddel", "delay", 300, 240, 60, nin=2, nout=1, ot=["bang"]),
        M("pr_ldstop", "stop", 380, 240, 44),
        M("pr_full1", "1", 300, 300, 26),
        M("pr_full0", "0", 340, 300, 26),
        O("pr_fulls", "s ---prerollFull", 300, 330, 120, nin=1, nout=0),
        O("pr_sizech", "change", 300, 110 + 200, 54),
        O("pr_szt", "t b b", 300, 340 + 4, 44, nin=1, nout=2, ot=["bang", "bang"]),
        O("pr_szgate", "gate 1", 300, 370, 54, nin=2, nout=1),
        M("pr_reset", "reset", 380, 370, 50),
    ]
    lines = [
        Ln("p_l", 0, "pr_rec", 0), Ln("p_r", 0, "pr_rec", 1),
        Ln("pr_arm", 0, "pr_armf", 0), Ln("pr_armf", 0, "pr_gate", 1),
        Ln("pr_hc", 0, "pr_hcinv", 0), Ln("pr_hcinv", 0, "pr_gate", 0),
        Ln("pr_gate", 0, "pr_run", 0),
        Ln("pr_hc", 0, "pr_hcsel", 0),
        Ln("pr_hcsel", 1, "pr_stop", 0),          # hasContent->1 : force stop
        Ln("pr_hcsel", 1, "pr_ldstop", 0),
        Ln("pr_hcsel", 1, "pr_full0", 0),
        Ln("pr_hcsel", 0, "pr_armf", 0),          # hasContent->0 : re-emit arm (bang f)
        Ln("pr_run", 0, "pr_runsel", 0),
        Ln("pr_runsel", 0, "pr_start", 0), Ln("pr_start", 0, "pr_rec", 0),
        Ln("pr_runsel", 0, "pr_lddel", 0),        # run->1 : start LED delay
        Ln("pr_runsel", 1, "pr_stop", 0),
        Ln("pr_runsel", 1, "pr_ldstop", 0),
        Ln("pr_runsel", 1, "pr_full0", 0),        # run->0 : full=0
        Ln("pr_stop", 0, "pr_rec", 0),
        Ln("pr_ldstop", 0, "pr_lddel", 0),
        Ln("pr_size", 0, "pr_lddel", 1),          # delay time = LoopLength ms
        Ln("pr_lddel", 0, "pr_full1", 0),         # one full ring pass -> full=1
        Ln("pr_full1", 0, "pr_fulls", 0), Ln("pr_full0", 0, "pr_fulls", 0),
        Ln("pr_size", 0, "pr_sizech", 0),
        Ln("pr_sizech", 0, "pr_szt", 0),
        Ln("pr_szt", 0, "pr_szgate", 1),
        Ln("pr_run", 0, "pr_szgate", 0),          # gate the restart on "running"
        Ln("pr_szgate", 0, "pr_reset", 0), Ln("pr_reset", 0, "pr_rec", 0),
        Ln("pr_szgate", 0, "pr_lddel", 0),        # restart delay
        Ln("pr_szgate", 0, "pr_full0", 0),
    ]
    return {
        "fileversion": 1,
        "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
        "classnamespace": "box",
        "rect": [40.0, 40.0, 800.0, 600.0],
        "boxes": boxes, "lines": lines,
    }


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    ids = {b.get("box", b)["id"] for b in root["boxes"]}
    assert "ingain_L" in ids and "ingain_R" in ids and "obj-29" in ids
    for n in ("p_preroll", "pr_armsend", "preroll_led", "pr_ledr", "preroll_lbl", "preroll_lbl2"):
        assert n not in ids, n

    root["boxes"] += [
        {"box": {"id": "p_preroll", "maxclass": "newobj", "text": "p Preroll",
                 "numinlets": 2, "numoutlets": 0, "patching_rect": [2600.0, 500.0, 70.0, 22.0],
                 "patcher": preroll_patcher()}},
        O("pr_armsend", "s ---prerollArm", 2600.0, 470.0, 110, nin=1, nout=0),
        O("pr_ledr", "r ---prerollFull", 2720.0, 470.0, 110, nin=0, nout=1),
        {"box": {"id": "preroll_led", "maxclass": "led", "numinlets": 1, "numoutlets": 1,
                 "outlettype": ["int"], "parameter_enable": 0,
                 "patching_rect": [2720.0, 500.0, 24.0, 24.0],
                 "presentation": 1, "presentation_rect": [906.0, 44.0, 14.0, 14.0],
                 "oncolor": [0.2, 0.85, 0.35, 1.0]}},
        {"box": {"id": "preroll_lbl", "maxclass": "comment", "text": "ARM", "numinlets": 1,
                 "numoutlets": 0, "patching_rect": [2600.0, 440.0, 40.0, 18.0],
                 "presentation": 1, "presentation_rect": [901.0, 12.0, 22.0, 12.0],
                 "textcolor": ORANGE, "fontsize": 8.0, "textjustification": 1}},
        {"box": {"id": "preroll_lbl2", "maxclass": "comment", "text": "FULL", "numinlets": 1,
                 "numoutlets": 0, "patching_rect": [2600.0, 458.0, 40.0, 18.0],
                 "presentation": 1, "presentation_rect": [898.0, 60.0, 26.0, 12.0],
                 "textcolor": ORANGE, "fontsize": 8.0, "textjustification": 1}},
    ]
    # promote the (dead) arm toggle into presentation
    obj29 = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "obj-29")
    obj29["presentation"] = 1
    obj29["presentation_rect"] = [906.0, 24.0, 14.0, 14.0]

    root["lines"] += [
        Ln("ingain_L", 0, "p_preroll", 0), Ln("ingain_R", 0, "p_preroll", 1),
        Ln("obj-29", 0, "pr_armsend", 0),
        Ln("pr_ledr", 0, "preroll_led", 0),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    for p, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {p} {d}")
    e = find_scope(load(OUT).patcher, "/")
    print("obj-29 OUT:", [(d, di) for (s, so, d, di) in e.lines() if s == "obj-29"])
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
