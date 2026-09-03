"""v6_197 -- handoff = exactly the MANUAL message, nothing else. Bisect start.

v6_196 didn't play; "loop less than half / off-beat" is consistent with the
handoff sending `window 0` (f 12000 default not holding -> $1 = 0). And v6_194
sent a correct window 0.114 and still didn't play while MAN (window 0.05) does
-- so a handoff-only send is the blocker.

v6_197 p PrerollCapture:
  loadmess 8000 -> pc_szf (plain f)                 -- seed the fraction default
  r ---size -> pc_szf                               -- update when it broadcasts
  r ---prerollCapture -> t b b:
     [1] bang pc_szf -> / 120000. -> maximum 0.01 -> pc_msg $1
     [0] bang pc_msg = "set ---thisBuffer, window $1, jump 0., play" -> s ---karmaMsg
         AND s ---dbgHandoff 1   (diag: did the message fire?)
  NOTHING ELSE. No ---hasContent, no ---prerollLoop, no ---regrid, no keep-alive.

Diag: add HND (r ---dbgHandoff) to the strip. MAN button kept.

If it plays -> re-add hasContent / prerollLoop / regrid one per build to find
the blocker. If not -> the rc_gate -> ---prerollCapture -> message path itself
differs from MAN.

    python phase3_file14_handoff_bare.py   # -> ../generated/ChopChop_v6_197.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

ORANGE = [1.0, 0.709803921568627, 0.196078431372549, 1.0]


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_196.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_197.amxd"


def O(i, t, x, y, w=120, nin=2, nout=1, ot=None):
    return {"box": {"id": i, "maxclass": "newobj", "text": t, "numinlets": nin,
                    "numoutlets": nout, "outlettype": ot if ot is not None else [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


def M(i, t, x, y, w=120):
    return {"box": {"id": i, "maxclass": "message", "text": t, "numinlets": 2, "numoutlets": 1,
                    "outlettype": [""], "patching_rect": [float(x), float(y), float(w), 20.0]}}


def prcap_patcher():
    B = [
        O("pc_trig", "r ---prerollCapture", 20, 20, 140, nin=0, nout=1),
        O("pc_lm", "loadmess 8000", 320, 16, 100, nin=1, nout=1),
        O("pc_szr", "r ---size", 320, 40, 90, nin=0, nout=1),
        O("pc_szf", "f", 320, 66, 30),
        O("pc_szdiv", "/ 120000.", 320, 92, 70),
        O("pc_szclamp", "maximum 0.01", 320, 118, 90),

        O("pc_t", "t b b", 20, 56, 44, nin=1, nout=2, ot=["bang", "bang"]),
        M("pc_msg", "set ---thisBuffer, window $1, jump 0., play", 20, 96, 290),
        O("pc_kmsg", "s ---karmaMsg", 20, 122, 110, nin=1, nout=0),
        M("pc_dbg", "1", 20, 148, 26), O("pc_dbgs", "s ---dbgHandoff", 56, 148, 120, nin=1, nout=0),
    ]
    L = [
        Ln("pc_lm", 0, "pc_szf", 0),
        Ln("pc_szr", 0, "pc_szf", 0),
        Ln("pc_szf", 0, "pc_szdiv", 0),
        Ln("pc_szdiv", 0, "pc_szclamp", 0),
        Ln("pc_szclamp", 0, "pc_msg", 1),

        Ln("pc_trig", 0, "pc_t", 0),
        Ln("pc_t", 1, "pc_szf", 0),          # refresh $1
        Ln("pc_t", 0, "pc_msg", 0),
        Ln("pc_msg", 0, "pc_kmsg", 0),
        Ln("pc_t", 0, "pc_dbg", 0), Ln("pc_dbg", 0, "pc_dbgs", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 700.0, 220.0], "boxes": B, "lines": L}


def num_diag(i, ch, prx, pry, lbl):
    return [
        {"box": {"id": i + "_r", "maxclass": "newobj", "text": "r " + ch, "numinlets": 0,
                 "numoutlets": 1, "outlettype": [""], "patching_rect": [2600.0, pry, 110.0, 20.0]}},
        {"box": {"id": i + "_n", "maxclass": "number", "numinlets": 1, "numoutlets": 2,
                 "outlettype": ["", "bang"], "patching_rect": [2720.0, pry, 70.0, 22.0],
                 "presentation": 1, "presentation_rect": [prx, pry - 200.0, 40.0, 15.0]}},
        {"box": {"id": i + "_l", "maxclass": "comment", "text": lbl, "numinlets": 1, "numoutlets": 0,
                 "patching_rect": [2800.0, pry, 40.0, 18.0], "presentation": 1,
                 "presentation_rect": [prx + 42.0, pry - 200.0, 24.0, 12.0],
                 "textcolor": ORANGE, "fontsize": 7.0}},
    ]


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    b = next(x.get("box", x) for x in root["boxes"] if x.get("box", x)["id"] == "p_prcap")
    b["patcher"] = prcap_patcher()

    ids = {x.get("box", x)["id"] for x in root["boxes"]}
    if "dg_hnd_r" not in ids:
        root["boxes"] += num_diag("dg_hnd", "---dbgHandoff", 888.0, 410.0, "HND")
        root["lines"].append(Ln("dg_hnd_r", 0, "dg_hnd_n", 0))

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    for p, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {p} {d}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
