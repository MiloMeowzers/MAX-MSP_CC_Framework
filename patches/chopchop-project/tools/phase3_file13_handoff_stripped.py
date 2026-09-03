"""v6_196 -- strip the handoff to exactly what the MANUAL button does.

v6_195 test: fraction was fine all along (int number box truncated 0.114 -> 0).
FRC 0.114283 = 13714/120000, SIZ 13714. MAN button plays instantly; the handoff
does not -- with HC=1 and CAP=120000 already set (MAN worked in that state), so
the blocker is a handoff send MAN doesn't do -> `s ---regrid` (whole size /
window / waveform cascade) is the suspect.

v6_196 p PrerollCapture:
  r ---prerollCapture -> t b b:
    [2] s ---prerollLoop 1
    [1] s ---hasContent 1
    [0] -> t b b: bang the fraction (r ---size -> f -> / 120000. -> maximum
         0.005), then fire `set ---thisBuffer, window $1, jump 0., play` ->
         s ---karmaMsg
  NO ---regrid, NO ---capturedMs.  Keep-alive metro unchanged.

MAN button + diag strip kept. If this plays a stable loop, ---regrid /
---capturedMs get added back one at a time (v6_197+).

    python phase3_file13_handoff_stripped.py   # -> ../generated/ChopChop_v6_196.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_195.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_196.amxd"


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
        O("pc_t", "t b b b", 20, 50, 70, nin=1, nout=3, ot=["bang", "bang", "bang"]),

        O("pc_szr", "r ---size", 320, 20, 90, nin=0, nout=1),
        O("pc_szf", "f 12000", 320, 46, 60),
        O("pc_szdiv", "/ 120000.", 320, 72, 70),
        O("pc_szclamp", "maximum 0.005", 320, 98, 100),

        M("pc_pl1", "1", 20, 84, 26), O("pc_pls", "s ---prerollLoop", 56, 84, 120, nin=1, nout=0),
        M("pc_hc1", "1", 20, 110, 26), O("pc_hcs", "s ---hasContent", 56, 110, 120, nin=1, nout=0),

        O("pc_pre", "t b b", 20, 140, 44, nin=1, nout=2, ot=["bang", "bang"]),
        M("pc_msg", "set ---thisBuffer, window $1, jump 0., play", 20, 168, 290),
        O("pc_kmsg", "s ---karmaMsg", 20, 194, 110, nin=1, nout=0),

        O("pc_plr", "r ---prerollLoop", 500, 66, 120, nin=0, nout=1),
        O("pc_kasz", "r ---size", 500, 40, 90, nin=0, nout=1),
        O("pc_kam", "metro 4000", 500, 92, 80, nin=2, nout=1, ot=["bang"]),
        M("pc_jm", "jump 0.", 500, 120, 60),
        O("pc_jms", "s ---karmaMsg", 500, 146, 110, nin=1, nout=0),

        O("pc_hcr", "r ---hasContent", 700, 40, 120, nin=0, nout=1),
        O("pc_hcsel", "sel 0", 700, 66, 44, nin=2, nout=2, ot=["bang", ""]),
        O("pc_ronr", "r ---recordOn", 840, 40, 110, nin=0, nout=1),
        M("pc_pl0", "0", 760, 92, 26), O("pc_pls2", "s ---prerollLoop", 760, 118, 120, nin=1, nout=0),
    ]
    L = [
        Ln("pc_trig", 0, "pc_t", 0),
        Ln("pc_szr", 0, "pc_szf", 0),
        Ln("pc_szf", 0, "pc_szdiv", 0),
        Ln("pc_szdiv", 0, "pc_szclamp", 0),
        Ln("pc_szclamp", 0, "pc_msg", 1),

        Ln("pc_t", 2, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),
        Ln("pc_t", 1, "pc_hc1", 0), Ln("pc_hc1", 0, "pc_hcs", 0),
        Ln("pc_t", 0, "pc_pre", 0),
        Ln("pc_pre", 1, "pc_szf", 0),           # refresh $1 from current ---size
        Ln("pc_pre", 0, "pc_msg", 0),
        Ln("pc_msg", 0, "pc_kmsg", 0),

        Ln("pc_kasz", 0, "pc_kam", 1), Ln("pc_plr", 0, "pc_kam", 0),
        Ln("pc_kam", 0, "pc_jm", 0), Ln("pc_jm", 0, "pc_jms", 0),

        Ln("pc_hcr", 0, "pc_hcsel", 0),
        Ln("pc_hcsel", 0, "pc_pl0", 0), Ln("pc_ronr", 0, "pc_pl0", 0),
        Ln("pc_pl0", 0, "pc_pls2", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 1000.0, 260.0], "boxes": B, "lines": L}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    b = next(x.get("box", x) for x in root["boxes"] if x.get("box", x)["id"] == "p_prcap")
    b["patcher"] = prcap_patcher()
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
