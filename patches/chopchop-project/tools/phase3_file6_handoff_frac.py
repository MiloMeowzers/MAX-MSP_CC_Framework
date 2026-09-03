"""v6_189 -- fix the window fraction (was 0 -> window 0 -> silence) + metro keep-alive.

v6_188: fraction diag reads 0 -> `window $1` = `window 0` -> no audio. `---size`
reached p PrerollCapture as 0 (0 on load before the menu resolves) and stuck in
`pc_fracf`.

Rewrite p PrerollCapture:
 - `pc_szf` (f) tracks ---size continuously. At capture: bang it -> `maximum 500`
   (never below 500 ms) -> `/ 120000.` -> `$1` of pc_msg (and -> ---pcFracDiag).
   Computed fresh each capture, floored, so it can't be 0.
 - keep-alive: `metro` (interval = r ---size, on/off = r ---prerollLoop) ->
   `jump 0.` -> s ---karmaMsg. Replaces the counter-carry (unreliable). Not a
   message cycle, so the sweep stays 27.
 - karma set/window/jump/play still fires LAST (after prerollLoop / capturedMs /
   hasContent / regrid).

Manual probe (pk_btn) and ---pcFracDiag number box kept.

    python phase3_file6_handoff_frac.py   # -> ../generated/ChopChop_v6_189.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_188.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_189.amxd"


def prcap_patcher():
    def O(i, t, x, y, w=120, nin=2, nout=1, ot=None):
        return {"box": {"id": i, "maxclass": "newobj", "text": t, "numinlets": nin,
                        "numoutlets": nout, "outlettype": ot if ot is not None else [""],
                        "patching_rect": [float(x), float(y), float(w), 20.0]}}

    def M(i, t, x, y, w=120):
        return {"box": {"id": i, "maxclass": "message", "text": t, "numinlets": 2, "numoutlets": 1,
                        "outlettype": [""], "patching_rect": [float(x), float(y), float(w), 20.0]}}

    B = [
        O("pc_trig", "r ---prerollCapture", 20, 20, 140, nin=0, nout=1),
        O("pc_t", "t b b b b b", 20, 50, 90, nin=1, nout=5,
          ot=["bang", "bang", "bang", "bang", "bang"]),
        M("pc_pl1", "1", 20, 78, 26), O("pc_pls", "s ---prerollLoop", 56, 78, 120, nin=1, nout=0),
        M("pc_cap", "120000", 20, 104, 60), O("pc_caps", "s ---capturedMs", 90, 104, 120, nin=1, nout=0),
        M("pc_hc1", "1", 20, 130, 26), O("pc_hcs", "s ---hasContent", 56, 130, 120, nin=1, nout=0),
        M("pc_rg", "bang", 20, 156, 40), O("pc_rgs", "s ---regrid", 64, 156, 90, nin=1, nout=0),
        O("pc_lastt", "t b b", 20, 184, 44, nin=1, nout=2, ot=["bang", "bang"]),

        # fresh, floored window fraction each capture
        O("pc_szr", "r ---size", 300, 20, 90, nin=0, nout=1),
        O("pc_szf", "f", 300, 46, 30),
        O("pc_szmax", "maximum 500", 300, 72, 80),
        O("pc_szdiv", "/ 120000.", 300, 98, 70),
        O("pc_fdiag", "s ---pcFracDiag", 300, 124, 120, nin=1, nout=0),

        M("pc_msg", "set ---thisBuffer, window $1, jump 0., play", 20, 216, 290),
        O("pc_kmsg", "s ---karmaMsg", 20, 242, 110, nin=1, nout=0),

        # keep-alive: metro while in a preroll loop
        O("pc_kasz", "r ---size", 480, 40, 90, nin=0, nout=1),
        O("pc_plr", "r ---prerollLoop", 480, 66, 120, nin=0, nout=1),
        O("pc_kam", "metro 4000", 480, 92, 80, nin=2, nout=1, ot=["bang"]),
        M("pc_jm", "jump 0.", 480, 120, 60),
        O("pc_jms", "s ---karmaMsg", 480, 146, 110, nin=1, nout=0),

        # ---prerollLoop clears
        O("pc_hcr", "r ---hasContent", 680, 40, 120, nin=0, nout=1),
        O("pc_hcsel", "sel 0", 680, 66, 44, nin=2, nout=2, ot=["bang", ""]),
        O("pc_ronr", "r ---recordOn", 820, 40, 110, nin=0, nout=1),
        M("pc_pl0", "0", 740, 92, 26), O("pc_pls2", "s ---prerollLoop", 740, 118, 120, nin=1, nout=0),
    ]
    L = [
        Ln("pc_trig", 0, "pc_t", 0),
        Ln("pc_t", 4, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),
        Ln("pc_t", 3, "pc_cap", 0), Ln("pc_cap", 0, "pc_caps", 0),
        Ln("pc_t", 2, "pc_hc1", 0), Ln("pc_hc1", 0, "pc_hcs", 0),
        Ln("pc_t", 1, "pc_rg", 0), Ln("pc_rg", 0, "pc_rgs", 0),
        Ln("pc_t", 0, "pc_lastt", 0),
        Ln("pc_lastt", 1, "pc_szf", 0),      # 1st: emit current ---size ...
        Ln("pc_lastt", 0, "pc_msg", 0),      # 2nd: fire the karma message

        Ln("pc_szr", 0, "pc_szf", 0),        # track ---size
        Ln("pc_szf", 0, "pc_szmax", 0),
        Ln("pc_szmax", 0, "pc_szdiv", 0),
        Ln("pc_szdiv", 0, "pc_msg", 1),      # -> $1
        Ln("pc_szdiv", 0, "pc_fdiag", 0),
        Ln("pc_msg", 0, "pc_kmsg", 0),

        Ln("pc_kasz", 0, "pc_kam", 1),       # metro interval = ---size
        Ln("pc_plr", 0, "pc_kam", 0),        # on/off = ---prerollLoop
        Ln("pc_kam", 0, "pc_jm", 0), Ln("pc_jm", 0, "pc_jms", 0),

        Ln("pc_hcr", 0, "pc_hcsel", 0),
        Ln("pc_hcsel", 0, "pc_pl0", 0), Ln("pc_ronr", 0, "pc_pl0", 0),
        Ln("pc_pl0", 0, "pc_pls2", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 980.0, 320.0], "boxes": B, "lines": L}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    pcap = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_prcap")
    pcap["patcher"] = prcap_patcher()

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
