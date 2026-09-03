"""v6_201 -- Phase 3 rebuild: preroll playback on groove~, not the karma set+window phantom.

Research (context.md 2026-09-04, karma~ 1.0 C source + help + user's own maxpat samples):
`karma~` 1.0 has no way to adopt a record~-filled buffer region as a real loop -- `set`
gives the whole allocation, `crop`/`size` fail in M4L. `groove~` does exactly this natively:
point it at ---thisBuffer, set loopstart/loopend in ms (inlets 1/2), `loop 1`, `startloop`,
drive inlet 0 with `sig~ 1.`. Confirmed by the user's `PlayPartOfSampleUsingGroove.maxpat`,
`groovebasics.maxpat`, `livecaptureinbuffer.maxpat`.

This file swaps the preroll capture handoff from karma-phantom to a real groove~ region loop.

 p Playback (obj-118) -- new groove~ engine:
   gv        groove~ ---thisBuffer 2      reads the same buffer the ring fills
   gv_sig    sig~ 1.                  -> gv[0]     private forward rate, NOT is_playing-gated
   gv_r      r ---gvMsg              -> gv[0]     set / loop 1 / startloop
   gv_lsr    r ---gvLoopStart        -> gv[1]     loopstart ms
   gv_ler    r ---gvLoopEnd          -> gv[2]     loopend ms
   gvxL/gvxR *~                      gv[0]/gv[1] * gv_gate    mix-in gain
   gv_gate   line~  <- gv_gm ($1 15) <- gv_gr (r ---prerollLoop)   0 normally, 1 on capture
   gv_plr    r ---prerollLoop -> gv_plsel (sel 0) -> gv_stopm (stop) -> gv[0]   stop on INIT
   gvmixL/R  +~   inserted between bmixL/bmixR and the p Playback audio outlets (obj-23/25)

 p PrerollCapture (p_prcap) -- rewritten, drops the phantom (pc_lm/pc_szdiv/pc_szclamp/
   pc_msg/pc_kmsg/pc_t):
   pc_trig (r ---prerollCapture) -> pc_seq (t b b b b b b), fires o5..o0:
     o5 -> bang pc_szf (f, <- r ---size) -> pc_le  (s ---gvLoopEnd)
     o4 -> pc_ls  "0"          -> pc_lss  (s ---gvLoopStart)
     o3 -> pc_setb "set ---thisBuffer" -> pc_gvs (s ---gvMsg)
     o2 -> pc_loop1 "loop 1"   -> pc_gvs
     o1 -> pc_start "startloop"-> pc_gvs
     o0 -> pc_open "1" -> pc_opens (s ---prerollLoop)  AND  pc_dbg "1" -> pc_dbgs

 root -- INIT closes the groove~ gain:
   obj-123[0] (soft INIT; also reached by full INIT and by load) -> ri_pl0 "0" -> s ---prerollLoop

 p Preroll (p_preroll) -- bound the ring to [0, ---size] so groove~'s region is the recent
   capture, not a stale 120 s rotation (record~ inlets 2/3 = start/end ms; DB- and
   sample-patch-verified -- the v6_187 revert was precautionary):
   pr_settle (ring-start bang) -> pr_sp0 "0" -> pr_rec[2]
   pr_settle + (r ---size) -> pr_endf (f) -> pr_rec[3]

    python phase3_file18_groove_preroll_engine.py   # -> ../generated/ChopChop_v6_201.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_199_USEREDIT.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_201.amxd"


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def nobj(bid, text, x, y, w=90.0, nin=1, nout=1, outtype=None):
    b = {"id": bid, "maxclass": "newobj", "text": text, "numinlets": nin,
         "numoutlets": nout, "patching_rect": [x, y, w, 22.0]}
    if outtype is not None:
        b["outlettype"] = outtype
    return {"box": b}


def nmsg(bid, text, x, y, w=44.0):
    return {"box": {"id": bid, "maxclass": "message", "text": text, "numinlets": 2,
                    "numoutlets": 1, "outlettype": [""], "patching_rect": [x, y, w, 20.0]}}


def has_line(pat, s, so, d, di):
    for e in pat["lines"]:
        pl = e.get("patchline", e)
        if pl["source"] == [s, so] and pl["destination"] == [d, di]:
            return True
    return False


def drop_line(pat, s, d):
    pat["lines"] = [e for e in pat["lines"]
                    if not (e.get("patchline", e)["source"][0] == s
                            and e.get("patchline", e)["destination"][0] == d)]


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher

    pb = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "obj-118")["patcher"]
    pc = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_prcap")["patcher"]
    pr = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_preroll")["patcher"]

    SIG = ["signal"]

    # ---------------------------------------------------------------- p Playback: groove~ engine
    pb["boxes"] += [
        nobj("gv", "groove~ ---thisBuffer 2", 900.0, 806.0, 150.0, nin=3, nout=3,
             outtype=["signal", "signal", "signal"]),
        nobj("gv_sig", "sig~ 1.", 900.0, 778.0, 46.0, outtype=SIG),
        nobj("gv_r", "r ---gvMsg", 1060.0, 750.0, 90.0, nin=0, outtype=[""]),
        nobj("gv_lsr", "r ---gvLoopStart", 1060.0, 778.0, 118.0, nin=0, outtype=[""]),
        nobj("gv_ler", "r ---gvLoopEnd", 1060.0, 806.0, 112.0, nin=0, outtype=[""]),
        nobj("gvxL", "*~", 900.0, 846.0, 32.0, nin=2, outtype=SIG),
        nobj("gvxR", "*~", 940.0, 846.0, 32.0, nin=2, outtype=SIG),
        nobj("gv_gate", "line~", 1000.0, 818.0, 44.0, nin=2, nout=2, outtype=["signal", "bang"]),
        nmsg("gv_gm", "$1 15", 1000.0, 790.0, 44.0),
        nobj("gv_gr", "r ---prerollLoop", 1000.0, 762.0, 112.0, nin=0, outtype=[""]),
        nobj("gv_plr", "r ---prerollLoop", 1150.0, 748.0, 112.0, nin=0, outtype=[""]),
        nobj("gv_plsel", "sel 0", 1150.0, 776.0, 40.0, nin=2, nout=2, outtype=["bang", ""]),
        nmsg("gv_stopm", "stop", 1150.0, 804.0, 40.0),
        nobj("gvmixL", "+~", 35.0, 715.0, 36.0, nin=2, outtype=SIG),
        nobj("gvmixR", "+~", 143.5, 715.0, 36.0, nin=2, outtype=SIG),
    ]
    # mix insert
    drop_line(pb, "bmixL", "obj-23")
    drop_line(pb, "bmixR", "obj-25")
    pb["lines"] += [
        Ln("gv_sig", 0, "gv", 0), Ln("gv_r", 0, "gv", 0),
        Ln("gv_lsr", 0, "gv", 1), Ln("gv_ler", 0, "gv", 2),
        Ln("gv", 0, "gvxL", 0), Ln("gv", 1, "gvxR", 0),
        Ln("gv_gr", 0, "gv_gm", 0), Ln("gv_gm", 0, "gv_gate", 0),
        Ln("gv_gate", 0, "gvxL", 1), Ln("gv_gate", 0, "gvxR", 1),
        Ln("gv_plr", 0, "gv_plsel", 0), Ln("gv_plsel", 0, "gv_stopm", 0), Ln("gv_stopm", 0, "gv", 0),
        Ln("bmixL", 0, "gvmixL", 0), Ln("gvxL", 0, "gvmixL", 1), Ln("gvmixL", 0, "obj-23", 0),
        Ln("bmixR", 0, "gvmixR", 0), Ln("gvxR", 0, "gvmixR", 1), Ln("gvmixR", 0, "obj-25", 0),
    ]

    # ---------------------------------------------------------------- p PrerollCapture: rewrite
    DROP = {"pc_lm", "pc_szdiv", "pc_szclamp", "pc_msg", "pc_kmsg", "pc_t"}
    pc["boxes"] = [b for b in pc["boxes"] if b.get("box", b)["id"] not in DROP]
    pc["lines"] = [e for e in pc["lines"]
                   if e.get("patchline", e)["source"][0] not in DROP
                   and e.get("patchline", e)["destination"][0] not in DROP]
    pc["boxes"] += [
        nobj("pc_seq", "t b b b b b b", 40.0, 70.0, 110.0, nin=1, nout=6, outtype=["bang"] * 6),
        nobj("pc_le", "s ---gvLoopEnd", 40.0, 150.0, 112.0, nout=0),
        nmsg("pc_ls", "0", 170.0, 110.0, 30.0),
        nobj("pc_lss", "s ---gvLoopStart", 170.0, 150.0, 118.0, nout=0),
        nmsg("pc_setb", "set ---thisBuffer", 300.0, 110.0, 112.0),
        nmsg("pc_loop1", "loop 1", 424.0, 110.0, 50.0),
        nmsg("pc_start", "startloop", 486.0, 110.0, 60.0),
        nobj("pc_gvs", "s ---gvMsg", 300.0, 150.0, 90.0, nout=0),
        nmsg("pc_open", "1", 560.0, 110.0, 30.0),
        nobj("pc_opens", "s ---prerollLoop", 560.0, 150.0, 112.0, nout=0),
    ]
    pc["lines"] += [
        Ln("pc_trig", 0, "pc_seq", 0),
        Ln("pc_seq", 5, "pc_szf", 0), Ln("pc_szf", 0, "pc_le", 0),
        Ln("pc_seq", 4, "pc_ls", 0), Ln("pc_ls", 0, "pc_lss", 0),
        Ln("pc_seq", 3, "pc_setb", 0), Ln("pc_setb", 0, "pc_gvs", 0),
        Ln("pc_seq", 2, "pc_loop1", 0), Ln("pc_loop1", 0, "pc_gvs", 0),
        Ln("pc_seq", 1, "pc_start", 0), Ln("pc_start", 0, "pc_gvs", 0),
        Ln("pc_seq", 0, "pc_open", 0), Ln("pc_open", 0, "pc_opens", 0),
        Ln("pc_seq", 0, "pc_dbg", 0),
    ]

    # ---------------------------------------------------------------- root: INIT closes the gate
    root["boxes"] += [
        nmsg("ri_pl0", "0", 812.0, 384.0, 26.0),
        nobj("ri_pls", "s ---prerollLoop", 812.0, 410.0, 112.0, nout=0),
    ]
    root["lines"] += [Ln("obj-123", 0, "ri_pl0", 0), Ln("ri_pl0", 0, "ri_pls", 0)]

    # ---------------------------------------------------------------- p Preroll: bound the ring
    pr["boxes"] += [
        nobj("pr_endf", "f", 250.0, 250.0, 44.0, nin=2, outtype=[""]),
        nobj("pr_szr2", "r ---size", 300.0, 222.0, 70.0, nin=0, outtype=[""]),
        nmsg("pr_sp0", "0", 200.0, 250.0, 26.0),
    ]
    pr["lines"] += [
        Ln("pr_szr2", 0, "pr_endf", 0),
        Ln("pr_settle", 0, "pr_endf", 0),
        Ln("pr_settle", 0, "pr_sp0", 0),
        Ln("pr_endf", 0, "pr_rec", 3),
        Ln("pr_sp0", 0, "pr_rec", 2),
    ]

    amx.save(OUT)

    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size})  cycles {total} (base {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth} {d}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
