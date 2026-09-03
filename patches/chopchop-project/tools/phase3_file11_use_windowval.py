"""v6_194 -- handoff uses the device's own ---windowVal instead of a home fraction.

State from v6_193 test: after Record -> FRC 0, PLY 0, HC 1, FUL 0, no audio.
The cascade runs (HC=1) but the fraction never computes: `s ---size` is
`change`-filtered, so the forced regrid recomputes an unchanged value and
nothing rebroadcasts.

The device ALREADY computes the window fraction:
  w_fsize <- (---size, ---regrid) -> w_div (/ ---capturedMs) -> w_clip -> w_mul
  (x ---reloop) -> s ---windowVal   -> also -> w_send (window ...) -> s ---karmaMsg
and re-runs it on every ---regrid (no `change` on that path).

So the handoff:
  pc_t: [4] s ---karmaMsg "set ---thisBuffer"       (point karma at the buffer)
        [3] s ---hasContent 1                        (fires the ---capturedMs latch)
        [2] s ---capturedMs 120000                   (override -> windowVal = ---size/120000)
        [1] s ---prerollLoop 1
        [0] s ---regrid  ->  device recomputes ---windowVal AND auto-sends
            `window <that>` to karma  ->  delay 60  ->
            s ---karmaMsg "set ---thisBuffer, window $1, jump 0., play"
            with $1 = r ---windowVal (maximum 0.01), a belt-and-braces re-send.

p Preroll's dead ---prerollFrac computation is removed. Diag FRC now shows
---windowVal.

    python phase3_file11_use_windowval.py   # -> ../generated/ChopChop_v6_194.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_193.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_194.amxd"


def O(i, t, x, y, w=120, nin=2, nout=1, ot=None):
    return {"box": {"id": i, "maxclass": "newobj", "text": t, "numinlets": nin,
                    "numoutlets": nout, "outlettype": ot if ot is not None else [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


def M(i, t, x, y, w=120):
    return {"box": {"id": i, "maxclass": "message", "text": t, "numinlets": 2, "numoutlets": 1,
                    "outlettype": [""], "patching_rect": [float(x), float(y), float(w), 20.0]}}


def IN(i, x, y):
    return {"box": {"id": i, "maxclass": "inlet", "numinlets": 0, "numoutlets": 1,
                    "outlettype": ["signal"], "patching_rect": [float(x), float(y), 30.0, 30.0]}}


def preroll_patcher():
    # same as v6_193 minus the dead ---prerollFrac chain (pr_szhold/frmax/frdiv/frs)
    B = [
        IN("p_l", 20, 20), IN("p_r", 70, 20),
        O("pr_rec", "record~ ---thisBuffer 2 @loop 1", 20, 100, 210, nin=2, nout=1, ot=["signal"]),
        O("pr_arm", "r ---prerollArm", 300, 20, 120, nin=0, nout=1),
        O("pr_hc", "r ---hasContent", 300, 46, 120, nin=0, nout=1),
        O("pr_size", "r ---size", 300, 72, 90, nin=0, nout=1),
        O("pr_ron", "r ---recordOn", 620, 20, 120, nin=0, nout=1),
        O("pr_at", "t i b", 300, 110, 44, nin=1, nout=2, ot=["int", "bang"]),
        O("pr_ht", "t b i", 430, 110, 44, nin=1, nout=2, ot=["bang", "int"]),
        O("pr_af", "f", 300, 140, 30),
        O("pr_hf", "f", 430, 140, 30),
        O("pr_hfinv", "== 0", 430, 168, 40),
        O("pr_want", "*", 300, 196, 40),
        O("pr_wantch", "change", 300, 222, 50),
        O("pr_wsel", "sel 1 0", 300, 248, 54, nin=3, nout=3, ot=["bang", "bang", ""]),
        O("pr_settle", "delay 150", 300, 278, 70, nin=2, nout=1, ot=["bang"]),
        M("pr_start", "reset, 1", 300, 306, 70),
        M("pr_stop", "0", 400, 306, 26),
        M("pr_settlestop", "stop", 380, 278, 44),
        O("pr_run1", "1", 470, 278, 26, nin=2, nout=1),
        O("pr_run0", "0", 500, 278, 26, nin=2, nout=1),
        O("pr_running", "f 0", 470, 306, 40),
        O("pr_ronsel", "sel 1", 620, 46, 44, nin=2, nout=2, ot=["bang", ""]),
        M("pr_ronstop", "0", 620, 72, 26),
        O("pr_lddel", "delay 4000", 300, 360, 80, nin=2, nout=1, ot=["bang"]),
        M("pr_ldstop", "stop", 400, 360, 44),
        M("pr_full1", "1", 300, 400, 26),
        M("pr_full0", "0", 340, 400, 26),
        O("pr_fulls", "s ---prerollFull", 300, 428, 120, nin=1, nout=0),
    ]
    L = [
        Ln("p_l", 0, "pr_rec", 0), Ln("p_r", 0, "pr_rec", 1),
        Ln("pr_arm", 0, "pr_at", 0),
        Ln("pr_at", 1, "pr_hf", 0), Ln("pr_at", 0, "pr_af", 0),
        Ln("pr_hc", 0, "pr_ht", 0),
        Ln("pr_ht", 1, "pr_hf", 0), Ln("pr_ht", 0, "pr_af", 0),
        Ln("pr_hf", 0, "pr_hfinv", 0), Ln("pr_hfinv", 0, "pr_want", 1),
        Ln("pr_af", 0, "pr_want", 0),
        Ln("pr_want", 0, "pr_wantch", 0), Ln("pr_wantch", 0, "pr_wsel", 0),
        Ln("pr_wsel", 0, "pr_settle", 0),
        Ln("pr_settle", 0, "pr_start", 0), Ln("pr_start", 0, "pr_rec", 0),
        Ln("pr_settle", 0, "pr_run1", 0), Ln("pr_run1", 0, "pr_running", 0),
        Ln("pr_settle", 0, "pr_lddel", 0),
        Ln("pr_wsel", 1, "pr_stop", 0), Ln("pr_stop", 0, "pr_rec", 0),
        Ln("pr_wsel", 1, "pr_settlestop", 0), Ln("pr_settlestop", 0, "pr_settle", 0),
        Ln("pr_wsel", 1, "pr_run0", 0), Ln("pr_run0", 0, "pr_running", 0),
        Ln("pr_wsel", 1, "pr_ldstop", 0), Ln("pr_ldstop", 0, "pr_lddel", 0),
        Ln("pr_wsel", 1, "pr_full0", 0),
        Ln("pr_ron", 0, "pr_ronsel", 0),
        Ln("pr_ronsel", 0, "pr_ronstop", 0), Ln("pr_ronstop", 0, "pr_rec", 0),
        Ln("pr_ronsel", 0, "pr_settlestop", 0),
        Ln("pr_ronsel", 0, "pr_run0", 0),
        Ln("pr_ronsel", 0, "pr_ldstop", 0),
        Ln("pr_size", 0, "pr_lddel", 1),
        Ln("pr_lddel", 0, "pr_full1", 0),
        Ln("pr_full1", 0, "pr_fulls", 0), Ln("pr_full0", 0, "pr_fulls", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 900.0, 480.0], "boxes": B, "lines": L}


def prcap_patcher():
    B = [
        O("pc_trig", "r ---prerollCapture", 20, 20, 140, nin=0, nout=1),
        O("pc_t", "t b b b b b", 20, 50, 90, nin=1, nout=5,
          ot=["bang", "bang", "bang", "bang", "bang"]),

        O("pc_wv", "r ---windowVal", 320, 20, 120, nin=0, nout=1),
        O("pc_wvf", "f 0.05", 320, 46, 50),
        O("pc_wvclamp", "maximum 0.01", 320, 72, 90),

        M("pc_set", "set ---thisBuffer", 20, 84, 120), O("pc_setk", "s ---karmaMsg", 150, 84, 100, nin=1, nout=0),
        M("pc_hc1", "1", 20, 110, 26), O("pc_hcs", "s ---hasContent", 56, 110, 120, nin=1, nout=0),
        M("pc_cap", "120000", 20, 136, 60), O("pc_caps", "s ---capturedMs", 90, 136, 120, nin=1, nout=0),
        M("pc_pl1", "1", 20, 162, 26), O("pc_pls", "s ---prerollLoop", 56, 162, 120, nin=1, nout=0),
        M("pc_rg", "bang", 20, 188, 40), O("pc_rgs", "s ---regrid", 64, 188, 90, nin=1, nout=0),

        O("pc_wait", "delay 60", 20, 216, 60, nin=2, nout=1, ot=["bang"]),
        O("pc_pre", "t b b", 20, 242, 44, nin=1, nout=2, ot=["bang", "bang"]),
        M("pc_msg", "set ---thisBuffer, window $1, jump 0., play", 20, 270, 290),
        O("pc_kmsg", "s ---karmaMsg", 20, 296, 110, nin=1, nout=0),

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
        Ln("pc_wv", 0, "pc_wvf", 0),
        Ln("pc_wvf", 0, "pc_wvclamp", 0), Ln("pc_wvclamp", 0, "pc_msg", 1),

        Ln("pc_t", 4, "pc_set", 0), Ln("pc_set", 0, "pc_setk", 0),
        Ln("pc_t", 3, "pc_hc1", 0), Ln("pc_hc1", 0, "pc_hcs", 0),
        Ln("pc_t", 2, "pc_cap", 0), Ln("pc_cap", 0, "pc_caps", 0),
        Ln("pc_t", 1, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),
        Ln("pc_t", 0, "pc_rg", 0), Ln("pc_rg", 0, "pc_rgs", 0),
        Ln("pc_t", 0, "pc_wait", 0),
        Ln("pc_wait", 0, "pc_pre", 0),
        Ln("pc_pre", 1, "pc_wvf", 0),          # refresh $1 from ---windowVal (regrid updated it)
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
            "classnamespace": "box", "rect": [40.0, 40.0, 1000.0, 340.0], "boxes": B, "lines": L}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    for bid in ("p_preroll", "p_prcap"):
        b = next(x.get("box", x) for x in root["boxes"] if x.get("box", x)["id"] == bid)
        b["patcher"] = preroll_patcher() if bid == "p_preroll" else prcap_patcher()

    # repoint FRC diag from ---prerollFrac to ---windowVal
    for b in root["boxes"]:
        bb = b.get("box", b)
        if bb["id"] == "dg_frc_r":
            assert bb["text"] == "r ---prerollFrac"
            bb["text"] = "r ---windowVal"

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
