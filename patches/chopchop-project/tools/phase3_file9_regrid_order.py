"""v6_192 -- the handoff's own regrid re-windows karma to 0. Fix the ordering.

Root cause of "handoff won't play but the manual message does": the handoff
sends `s ---regrid`, which drives w_fsize -> ... -> w_send (s ---karmaMsg) ->
`window clip(---size / ---capturedMs)`. With ---capturedMs = 120000 and ---size
stale (0), that is `window 0` -> karma silenced, AFTER my correct window.

v6_192:
 - p PrerollCapture: pc_t order is capturedMs / hasContent / prerollLoop /
   regrid, THEN `deferlow -> pc_pre` -> refresh $1 from ---prerollFrac ->
   fire `set ---thisBuffer, window $1, jump 0., play`. The deferlow lets any
   deferred ---size recompute from the regrid land first, and the karma
   message is the LAST thing karma hears.
 - p Preroll: ---prerollFrac now recomputes on `r ---regrid` and on loadbang
   (via an f holding ---size), not only on a ---size change -- so the value is
   fresh whenever the handoff's regrid fires.

    python phase3_file9_regrid_order.py   # -> ../generated/ChopChop_v6_192.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_191.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_192.amxd"


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
    B = [
        IN("p_l", 20, 20), IN("p_r", 70, 20),
        O("pr_rec", "record~ ---thisBuffer 2 @loop 1", 20, 100, 210, nin=2, nout=1, ot=["signal"]),

        O("pr_arm", "r ---prerollArm", 300, 20, 120, nin=0, nout=1),
        O("pr_hc", "r ---hasContent", 300, 46, 120, nin=0, nout=1),
        O("pr_size", "r ---size", 300, 72, 90, nin=0, nout=1),
        O("pr_ron", "r ---recordOn", 620, 20, 120, nin=0, nout=1),
        O("pr_regr", "r ---regrid", 720, 72, 90, nin=0, nout=1),
        O("pr_lb", "loadbang", 720, 20, 60, nin=1, nout=1, ot=["bang"]),
        O("pr_lbd", "deferlow", 720, 46, 60, nin=1, nout=1),

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

        # --- window fraction: f-held ---size, recomputed on size / regrid / load ---
        O("pr_szhold", "f", 560, 46, 30),
        O("pr_frmax", "maximum 500", 560, 78, 80),
        O("pr_frdiv", "/ 120000.", 560, 104, 70),
        O("pr_frs", "s ---prerollFrac", 560, 130, 120, nin=1, nout=0),
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

        # fraction
        Ln("pr_size", 0, "pr_szhold", 0),            # store + emit on size change
        Ln("pr_regr", 0, "pr_szhold", 0),            # bang -> re-emit on regrid
        Ln("pr_lb", 0, "pr_lbd", 0), Ln("pr_lbd", 0, "pr_szhold", 0),   # and on load
        Ln("pr_szhold", 0, "pr_frmax", 0),
        Ln("pr_frmax", 0, "pr_frdiv", 0), Ln("pr_frdiv", 0, "pr_frs", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 920.0, 500.0], "boxes": B, "lines": L}


def prcap_patcher():
    B = [
        O("pc_trig", "r ---prerollCapture", 20, 20, 140, nin=0, nout=1),
        O("pc_t", "t b b b b b", 20, 50, 90, nin=1, nout=5,
          ot=["bang", "bang", "bang", "bang", "bang"]),
        O("pc_fr", "r ---prerollFrac", 320, 20, 120, nin=0, nout=1),
        O("pc_frf", "f 0.0333", 320, 46, 60),

        M("pc_cap", "120000", 20, 84, 60), O("pc_caps", "s ---capturedMs", 90, 84, 120, nin=1, nout=0),
        M("pc_hc1", "1", 20, 110, 26), O("pc_hcs", "s ---hasContent", 56, 110, 120, nin=1, nout=0),
        M("pc_pl1", "1", 20, 136, 26), O("pc_pls", "s ---prerollLoop", 56, 136, 120, nin=1, nout=0),
        M("pc_rg", "bang", 20, 162, 40), O("pc_rgs", "s ---regrid", 64, 162, 90, nin=1, nout=0),

        O("pc_def", "deferlow", 20, 190, 60, nin=1, nout=1),
        O("pc_pre", "t b b", 20, 216, 44, nin=1, nout=2, ot=["bang", "bang"]),
        M("pc_msg", "set ---thisBuffer, window $1, jump 0., play", 20, 244, 290),
        O("pc_kmsg", "s ---karmaMsg", 20, 270, 110, nin=1, nout=0),

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
        Ln("pc_fr", 0, "pc_frf", 0),
        Ln("pc_frf", 0, "pc_msg", 1),

        Ln("pc_t", 4, "pc_cap", 0), Ln("pc_cap", 0, "pc_caps", 0),
        Ln("pc_t", 3, "pc_hc1", 0), Ln("pc_hc1", 0, "pc_hcs", 0),
        Ln("pc_t", 2, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),
        Ln("pc_t", 1, "pc_rg", 0), Ln("pc_rg", 0, "pc_rgs", 0),
        Ln("pc_t", 0, "pc_def", 0),
        Ln("pc_def", 0, "pc_pre", 0),
        Ln("pc_pre", 1, "pc_frf", 0),           # refresh $1 (now regrid has updated ---prerollFrac)
        Ln("pc_pre", 0, "pc_msg", 0),           # fire karma message LAST
        Ln("pc_msg", 0, "pc_kmsg", 0),

        Ln("pc_kasz", 0, "pc_kam", 1), Ln("pc_plr", 0, "pc_kam", 0),
        Ln("pc_kam", 0, "pc_jm", 0), Ln("pc_jm", 0, "pc_jms", 0),

        Ln("pc_hcr", 0, "pc_hcsel", 0),
        Ln("pc_hcsel", 0, "pc_pl0", 0), Ln("pc_ronr", 0, "pc_pl0", 0),
        Ln("pc_pl0", 0, "pc_pls2", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 1000.0, 320.0], "boxes": B, "lines": L}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    for bid in ("p_preroll", "p_prcap"):
        b = next(x.get("box", x) for x in root["boxes"] if x.get("box", x)["id"] == bid)
        b["patcher"] = preroll_patcher() if bid == "p_preroll" else prcap_patcher()
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
