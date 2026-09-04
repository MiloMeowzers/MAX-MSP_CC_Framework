"""v6_203 -- Phase 5 file 2: bar-locked substrate + fast-render Commit.

Base v6_202. Logic-only; NO presentation / position / openrect change.

Fixes the v6_202 test failures -- no beat alignment; the committed region landed
~2 beats off a bar line -- and restores a REAL karma master so slice / reverse /
DSP / UI / overlay work again (v6_185-level function), via a fast-render Commit.

Verified from karma~.c 1.0: `record` advances position by speed*srscale per
sample (clamped to loop/1024, ~375x for a 4-bar loop); the loop length is the
max position reached; ipoke~ linear-interpolates the gaps for speed>1. So an
8x record pass fed 8x-fast audio -> a real bounded loop of the correct length
at 1x pitch. User bench-confirmed 8x renders and plays back matching source.

------------------------------------------------------------------- what changes

p TempoTranslate
  + tt_bms  s ---barMs  <- r_barms[0]      (bar length ms, on every size recompute)

p RollCapture  -- position tracking reworked; ring bar-bounded; arm bar-synced
  DROP the snapshot~-on-record~-sync chain (rc_snap/rc_posms/rc_poss) and the
  rc_on/rc_rst messages; DROP s ---rollWritePos.
  Ring bound: r ---barMs -> rc_bmf f -> rc_rb (floor 120000/barMs) = ringBars ->
    rc_ru (ringBars*barMs) = ---ringUsedMs -> rc_rec[3]; 0 -> rc_rec[2].
    record~ now wraps on an exact integer-bar boundary.
  Bar count -> grab end:  rc_edge -> rc_bt (t b b).  rc_bt[1] advances rc_cnt.
    rc_cnt -> s ---dbgBar (SPD, unchanged) and -> rc_sub (cnt - armRef) ->
    rc_mod (% ringBars) = fold -> rc_endx (fold*barMs) -> s ---rollEndMs.
    ---rollEndMs is an EXACT integer-bar position -- no phasor snapshot, so no
    2-beat offset.  armRef is latched (rc_cntf/rc_armbar) on the arm bar so
    fold restarts at 0 when the roll starts.
  Arm bar-sync:  rc_armsel (sel 1 0).  armed(1) -> rc_pend "1" -> rc_pendf.
    disarmed(0) -> rc_off "0" -> rc_rec[0], rc_pend0 "0" -> rc_pendf.
    rc_bt[0] -> rc_pendf (bang) -> rc_pchk (sel 1): on 1 ->
      rc_astart "reset, 1" -> rc_rec[0]   (roll begins ON the downbeat)
      rc_cntf (bang) -> rc_armbar         (latch armRef = current bar count)
      rc_pclr "0" -> rc_pendf
  Drift/wrap realign:  rc_mod -> rc_fz (sel 0): fold==0 -> rc_wreset "reset" ->
      rc_rec[0]  (record~ head snaps back to bar 0 exactly when it would wrap).

p PrerollCapture  -- becomes the Commit orchestrator (auto first, manual after)
  Auto-first:  r ---prerollFull -> pc_fsel (sel 1) -> pc_fgate (gate, open while
    r ---hasContent == 0) -> pc_fpend "1" -> pc_fpf.  r ---dbgBar (a per-bar
    tick) -> pc_fbang -> pc_fpf (bang) -> pc_fchk (sel 1) -> s ---prerollCapture
    (the same trigger the manual Record path already uses) + clear pc_fpf.
  On ---prerollCapture:  pc_seq (t b b b b b b), outlets 6..0:
    o6 latch end/barMs/size/ringUsed into cold f-holds
    grab:  sizeMs = round(size/barMs)*barMs ; start = end - sizeMs ;
           wrap = start < 0
    o5..o1 the audible groove~ bridge (existing engine, 1x):
           s ---gvMsg "set ---rollBuf" ; s ---gvLoopStart=max(0,start) ;
           s ---gvLoopEnd=end ; s ---gvMsg "loop 1" ; s ---gvMsg "startloop" ;
           s ---prerollLoop 1
    o0 if NOT wrap: s ---commitGo  [start end (sizeMs/8)]   (a 3-float list)
       if wrap: s ---prerollCapture again (defer one bar; the wrapped-grab
       two-segment render is a v6_204 item)

p FastRender  -- NEW root subpatcher, on r ---commitGo
  unpack f f f  (start, end, renderMs).  right-to-left fire = renderMs, end,
    start; sprintf "%g 0. %g %g" (start,end,renderMs) fed cold end/renderMs then
    hot start -> fr_line line~ -> fr_play play~ ---rollBuf 2 ->
    send~ ---renderL / ---renderR.
  start also -> fr_kt (t b b): right -> line~ list is already built ; left ->
    fr_ks (t b b b b):
      o3  "1" -> s ---renderActive
      o2  "stop" -> s ---karmaMsg
      o1  "record" -> s ---karmaMsg ; and -> fr_dl delay <renderMs>
      o0  (spare)
    fr_dl -> "play" -> s ---karmaMsg ; "0" -> s ---renderActive ; bang ->
      s ---regrid ; "1" -> s ---hasContent ; delay 25 -> "0" -> s ---prerollLoop

p Playback  -- record source + karma-A speed switched for the render
  karma A speed:  remove obj-7[0] -> obj-20[2].  fr_add (+~): obj-7[0] -> [0],
    fr_boost (line~) -> [1], fr_add[0] -> obj-20[2].  fr_boost <- fr_bsel
    (sel 1 0 on r ---renderActive) -> "7. 2" / "0. 5".
  karma A record source:  remove obj-34[0]->obj-20[0], obj-29[0]->obj-20[1].
    fr_recL (selector~ 2): obj-34[0]->[1], receive~ ---renderL->[2],
      fr_ract (+1 on r ---renderActive)->[0], out -> obj-20[0].
    fr_recR: obj-29[0]->[1], receive~ ---renderR->[2], fr_ract[0]->[0],
      out -> obj-20[1].
  fr_rainit  loadmess 0 -> s ---renderActive   (selectors default to the live
    path; boost stays at 0).

New channels: ---barMs ---rollEndMs ---ringUsedMs ---renderActive ---renderL~
  ---renderR~ ---commitGo.   Dropped: ---rollWritePos.

    python phase3_file20_fastrender_commit.py   # -> ../generated/ChopChop_v6_203.amxd
"""
from pathlib import Path
import copy

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_202.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_203.amxd"


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def O(bid, text, x, y, w=90.0, nin=1, nout=1, ot=None):
    b = {"id": bid, "maxclass": "newobj", "text": text, "numinlets": nin,
         "numoutlets": nout, "patching_rect": [float(x), float(y), float(w), 22.0]}
    if ot is not None:
        b["outlettype"] = ot
    return {"box": b}


def M(bid, text, x, y, w=60.0):
    return {"box": {"id": bid, "maxclass": "message", "text": text, "numinlets": 2,
                    "numoutlets": 1, "outlettype": [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


def drop(pat, pred):
    pat["lines"] = [e for e in pat["lines"] if not pred(e.get("patchline", e))]


def has_box(pat, bid):
    return any(b.get("box", b)["id"] == bid for b in pat["boxes"])


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher

    def find(pat, pred):
        for b in pat.get("boxes", []):
            bx = b.get("box", b)
            if pred(bx):
                return bx
            if isinstance(bx.get("patcher"), dict):
                r = find(bx["patcher"], pred)
                if r:
                    return r

    pb = find(root, lambda x: x.get("text") == "p Playback")["patcher"]
    tt = find(root, lambda x: x.get("text") == "p TempoTranslate")["patcher"]
    pc = find(root, lambda x: x.get("text") == "p PrerollCapture")["patcher"]
    rc = find(root, lambda x: x.get("text") == "p RollCapture")["patcher"]
    pr = find(root, lambda x: x.get("text") == "p Preroll")["patcher"]
    SIG = ["signal"]
    APPV = copy.deepcopy(root.get("appversion", {"major": 9, "minor": 1, "revision": 4}))

    # ===================================================== p TempoTranslate
    tt["boxes"].append(O("tt_bms", "s ---barMs", 700.0, 40.0, 90.0, nout=0))
    tt["lines"].append(Ln("r_barms", 0, "tt_bms", 0))

    # ===================================================== p Preroll
    # v6_202 already cut audio into pr_rec (record~ ---thisBuffer).  Fully retire it:
    # cut its remaining reset/1/0 control so it never writes ---thisBuffer -- otherwise
    # it fights karma's fast-render record pass on the same buffer.  The FUL-LED /
    # ---prerollFull timer chain (pr_settle -> pr_lddel -> pr_full1) is untouched.
    drop(pr, lambda pl: pl["destination"][0] == "pr_rec")

    # ===================================================== p RollCapture
    for bid in ("rc_snap", "rc_posms", "rc_poss", "rc_on", "rc_rst"):
        rc["boxes"] = [b for b in rc["boxes"] if b.get("box", b)["id"] != bid]
    drop(rc, lambda pl: pl["source"][0] in ("rc_snap", "rc_posms", "rc_poss", "rc_on",
                                            "rc_rst", "rc_edge", "rc_armsel", "rc_cnt")
         or pl["destination"][0] in ("rc_snap", "rc_posms", "rc_poss", "rc_on", "rc_rst"))
    # surviving cords now: rcp_l/r->rc_rec ; rc_arm->rc_armsel ;
    #   rc_ph->rc_dl->rc_lt->rc_edge ; rc_off->rc_rec

    rc["boxes"] += [
        O("rc_bm", "r ---barMs", 300.0, 150.0, 90.0, nin=0, ot=[""]),
        O("rc_bmf", "f 2000.", 300.0, 178.0, 60.0, nin=2, ot=[""]),
        O("rc_rb", "expr floor(120000./$f1)", 300.0, 206.0, 170.0, nin=1, ot=[""]),
        O("rc_ru", "expr $f1*$f2", 300.0, 234.0, 120.0, nin=2, ot=[""]),
        O("rc_rus", "s ---ringUsedMs", 300.0, 262.0, 110.0, nout=0),
        M("rc_zero", "0", 470.0, 234.0, 26.0),
        O("rc_bt", "t b b", 20.0, 300.0, 50.0, nin=1, nout=2, ot=["bang", "bang"]),
        O("rc_sub", "- 0", 90.0, 372.0, 60.0, nin=2, ot=[""]),
        O("rc_cntf", "f", 150.0, 336.0, 40.0, nin=2, ot=[""]),
        O("rc_armbar", "f", 150.0, 372.0, 40.0, nin=2, ot=[""]),
        O("rc_mod", "% 60", 90.0, 400.0, 60.0, nin=2, ot=[""]),
        O("rc_endx", "expr $f1*$f2", 90.0, 428.0, 120.0, nin=2, ot=[""]),
        O("rc_ends", "s ---rollEndMs", 90.0, 456.0, 110.0, nout=0),
        O("rc_folds", "s ---rollFold", 20.0, 484.0, 110.0, nout=0),
        M("rc_pend", "1", 380.0, 320.0, 26.0),
        M("rc_pend0", "0", 410.0, 320.0, 26.0),
        O("rc_pendf", "f 0", 380.0, 348.0, 50.0, nin=2, ot=[""]),
        O("rc_pchk", "sel 1", 380.0, 376.0, 50.0, nin=2, nout=2, ot=["bang", ""]),
        M("rc_astart", "reset, 1", 440.0, 404.0, 70.0),
        M("rc_pclr", "0", 380.0, 404.0, 26.0),
        O("rc_fz", "sel 0", 230.0, 428.0, 44.0, nin=2, nout=2, ot=["bang", ""]),
        M("rc_wreset", "reset", 230.0, 456.0, 50.0),
    ]
    rc["lines"] += [
        Ln("rc_edge", 0, "rc_bt", 0),
        Ln("rc_bt", 1, "rc_cnt", 0),
        Ln("rc_cnt", 0, "rc_bars", 0),
        Ln("rc_cnt", 0, "rc_sub", 0),
        Ln("rc_cnt", 0, "rc_cntf", 1),
        Ln("rc_armbar", 0, "rc_sub", 1),
        Ln("rc_sub", 0, "rc_mod", 0),
        Ln("rc_mod", 0, "rc_endx", 0),
        Ln("rc_endx", 0, "rc_ends", 0),
        Ln("rc_mod", 0, "rc_folds", 0),
        Ln("rc_mod", 0, "rc_fz", 0),
        Ln("rc_fz", 0, "rc_wreset", 0),
        Ln("rc_wreset", 0, "rc_rec", 0),
        # ring bound
        Ln("rc_bm", 0, "rc_bmf", 0),
        Ln("rc_bmf", 0, "rc_rb", 0),
        Ln("rc_bmf", 0, "rc_ru", 1),
        Ln("rc_bmf", 0, "rc_endx", 1),
        Ln("rc_rb", 0, "rc_ru", 0),
        Ln("rc_rb", 0, "rc_mod", 1),
        Ln("rc_ru", 0, "rc_rus", 0),
        Ln("rc_ru", 0, "rc_rec", 3),
        Ln("rc_rb", 0, "rc_zero", 0),
        Ln("rc_zero", 0, "rc_rec", 2),
        # arm
        Ln("rc_armsel", 0, "rc_pend", 0),
        Ln("rc_pend", 0, "rc_pendf", 0),
        Ln("rc_armsel", 1, "rc_pend0", 0),
        Ln("rc_armsel", 1, "rc_off", 0),
        Ln("rc_pend0", 0, "rc_pendf", 0),
        Ln("rc_bt", 0, "rc_pendf", 0),
        Ln("rc_pendf", 0, "rc_pchk", 0),
        Ln("rc_pchk", 0, "rc_astart", 0),
        Ln("rc_astart", 0, "rc_rec", 0),
        Ln("rc_pchk", 0, "rc_cntf", 0),
        Ln("rc_cntf", 0, "rc_armbar", 0),
        Ln("rc_pchk", 0, "rc_pclr", 0),
        Ln("rc_pclr", 0, "rc_pendf", 0),
    ]

    # ===================================================== p PrerollCapture
    for bid in ("pc_szf", "pc_dbg", "pc_dbgs", "pc_le", "pc_lss", "pc_setb", "pc_loop1",
                "pc_start", "pc_gvs", "pc_open", "pc_opens", "pc_we", "pc_wef", "pc_ssub",
                "pc_swrap", "pc_szr", "pc_seq"):
        pc["boxes"] = [b for b in pc["boxes"] if b.get("box", b)["id"] != bid]
    pc["lines"] = []   # rebuild PrerollCapture wiring from scratch (pc_trig kept)
    if not has_box(pc, "pc_trig"):
        pc["boxes"].append(O("pc_trig", "r ---prerollCapture", 20.0, 20.0, 140.0, nin=0, ot=[""]))

    pc["boxes"] += [
        # --- auto-first-commit arming
        O("pc_full", "r ---prerollFull", 320.0, 20.0, 120.0, nin=0, ot=[""]),
        O("pc_fsel", "sel 1", 320.0, 48.0, 44.0, nin=2, nout=2, ot=["bang", ""]),
        O("pc_hcr", "r ---hasContent", 470.0, 20.0, 120.0, nin=0, ot=[""]),
        O("pc_hcinv", "== 0", 470.0, 48.0, 44.0, nin=2, ot=[""]),
        O("pc_fgate", "gate 1 0", 320.0, 80.0, 60.0, nin=2, ot=[""]),
        M("pc_fpend", "1", 320.0, 110.0, 26.0),
        O("pc_fpf", "f 0", 320.0, 138.0, 44.0, nin=2, ot=[""]),
        O("pc_fbarr", "r ---dbgBar", 470.0, 110.0, 90.0, nin=0, ot=[""]),
        O("pc_fbang", "t b", 470.0, 138.0, 30.0, nin=1, ot=["bang"]),
        O("pc_fchk", "sel 1", 320.0, 166.0, 44.0, nin=2, nout=2, ot=["bang", ""]),
        M("pc_fclr", "0", 380.0, 166.0, 26.0),
        O("pc_fcs", "s ---prerollCapture", 320.0, 194.0, 140.0, nout=0),
        # --- the commit
        O("pc_seq", "t b b b b b b", 20.0, 60.0, 130.0, nin=1, nout=7, ot=["bang"] * 7),
        O("pc_end", "r ---rollEndMs", 20.0, 96.0, 110.0, nin=0, ot=[""]),
        O("pc_endf", "f", 20.0, 124.0, 40.0, nin=2, ot=[""]),
        O("pc_bmr", "r ---barMs", 150.0, 96.0, 90.0, nin=0, ot=[""]),
        O("pc_bmf", "f 2000.", 150.0, 124.0, 60.0, nin=2, ot=[""]),
        O("pc_szr", "r ---size", 260.0, 96.0, 80.0, nin=0, ot=[""]),
        O("pc_szf", "f", 260.0, 124.0, 40.0, nin=2, ot=[""]),
        O("pc_rur", "r ---ringUsedMs", 360.0, 96.0, 110.0, nin=0, ot=[""]),
        O("pc_ruf", "f", 360.0, 124.0, 40.0, nin=2, ot=[""]),
        O("pc_szsnap", "expr round($f2/$f1)*$f1", 150.0, 160.0, 190.0, nin=2, ot=[""]),
        O("pc_startx", "expr $f1-$f2", 20.0, 190.0, 120.0, nin=2, ot=[""]),
        O("pc_wrapx", "expr ($f1<0.)?1:0", 20.0, 218.0, 130.0, nin=1, ot=[""]),
        O("pc_gvlo", "expr ($f1<0.)?0.:$f1", 150.0, 246.0, 150.0, nin=1, ot=[""]),
        O("pc_rmsx", "expr $f1/8.", 260.0, 190.0, 90.0, nin=1, ot=[""]),
        # bridge
        M("pc_gset", "set ---rollBuf", 420.0, 300.0, 110.0),
        M("pc_gl1", "loop 1", 420.0, 328.0, 60.0),
        M("pc_gsl", "startloop", 420.0, 356.0, 70.0),
        O("pc_gvs", "s ---gvMsg", 420.0, 384.0, 90.0, nout=0),
        O("pc_les", "s ---gvLoopEnd", 300.0, 300.0, 110.0, nout=0),
        O("pc_lss", "s ---gvLoopStart", 150.0, 300.0, 110.0, nout=0),
        M("pc_pl1", "1", 540.0, 328.0, 26.0),
        O("pc_pls", "s ---prerollLoop", 540.0, 356.0, 110.0, nout=0),
        # commit-go vs defer-one-bar (wrapped grab -> re-arm the same next-bar retry
        # the auto-first path uses; do NOT re-send ---prerollCapture in this tick or
        # wrap stays true and it loops)
        O("pc_gate", "gate 2", 20.0, 300.0, 90.0, nin=2, nout=2, ot=["bang", "bang"]),
        O("pc_wsel", "+ 1", 20.0, 274.0, 40.0, nin=2, ot=[""]),
        O("pc_sthold", "f", 200.0, 220.0, 40.0, nin=2, ot=[""]),
        O("pc_pk", "pack f f f", 20.0, 340.0, 120.0, nin=3, ot=[""]),
        O("pc_go", "s ---commitGo", 20.0, 396.0, 100.0, nout=0),
    ]
    pc["lines"] += [
        # auto-first
        Ln("pc_full", 0, "pc_fsel", 0),
        Ln("pc_hcr", 0, "pc_hcinv", 0),
        Ln("pc_hcinv", 0, "pc_fgate", 0),
        Ln("pc_fsel", 0, "pc_fgate", 1),
        Ln("pc_fgate", 0, "pc_fpend", 0),
        Ln("pc_fpend", 0, "pc_fpf", 0),
        Ln("pc_fbarr", 0, "pc_fbang", 0),
        Ln("pc_fbang", 0, "pc_fpf", 0),
        Ln("pc_fpf", 0, "pc_fchk", 0),
        Ln("pc_fchk", 0, "pc_fclr", 0),
        Ln("pc_fclr", 0, "pc_fpf", 0),
        Ln("pc_fchk", 0, "pc_fcs", 0),
        # trigger -> seq
        Ln("pc_trig", 0, "pc_seq", 0),
        # o6: latch inputs
        Ln("pc_end", 0, "pc_endf", 1), Ln("pc_seq", 6, "pc_endf", 0),
        Ln("pc_bmr", 0, "pc_bmf", 1), Ln("pc_seq", 6, "pc_bmf", 0),
        Ln("pc_szr", 0, "pc_szf", 1), Ln("pc_seq", 6, "pc_szf", 0),
        Ln("pc_rur", 0, "pc_ruf", 1), Ln("pc_seq", 6, "pc_ruf", 0),
        # compute  (o6 fan fires ruf, szf, bmf, endf -- bmf drives szsnap so szf is ready;
        #           endf fires last so startx sees a settled szsnap)
        Ln("pc_bmf", 0, "pc_szsnap", 0), Ln("pc_szf", 0, "pc_szsnap", 1),
        Ln("pc_endf", 0, "pc_startx", 0), Ln("pc_szsnap", 0, "pc_startx", 1),
        Ln("pc_startx", 0, "pc_wrapx", 0),
        Ln("pc_startx", 0, "pc_gvlo", 0),
        Ln("pc_szsnap", 0, "pc_rmsx", 0),
        # bridge (o5..o1)
        Ln("pc_seq", 5, "pc_gset", 0), Ln("pc_gset", 0, "pc_gvs", 0),
        Ln("pc_gvlo", 0, "pc_lss", 0), Ln("pc_endf", 0, "pc_les", 0),
        Ln("pc_seq", 4, "pc_gl1", 0), Ln("pc_gl1", 0, "pc_gvs", 0),
        Ln("pc_seq", 3, "pc_gsl", 0), Ln("pc_gsl", 0, "pc_gvs", 0),
        Ln("pc_seq", 2, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),
        # list assembly: end/renderMs stored cold into pc_pk on o6; start stored
        # silently into pc_sthold (f right inlet).  wrap flag sets pc_gate's route
        # on o6.  Nothing emits until o0 bangs pc_sthold -> start -> pc_pk fires
        # the full list once, through the already-routed gate.
        Ln("pc_startx", 0, "pc_sthold", 1),
        Ln("pc_endf", 0, "pc_pk", 1),
        Ln("pc_rmsx", 0, "pc_pk", 2),
        Ln("pc_wrapx", 0, "pc_wsel", 0),
        Ln("pc_wsel", 0, "pc_gate", 0),
        Ln("pc_seq", 0, "pc_sthold", 0),
        Ln("pc_sthold", 0, "pc_pk", 0),
        Ln("pc_pk", 0, "pc_gate", 1),
        Ln("pc_gate", 0, "pc_go", 0),
        Ln("pc_gate", 1, "pc_fpend", 0),
    ]

    # ===================================================== p FastRender (NEW)
    fr = {
        "fileversion": 1, "appversion": copy.deepcopy(APPV), "classnamespace": "box",
        "rect": [0.0, 0.0, 760.0, 460.0],
        "boxes": [
            O("fr_go", "r ---commitGo", 20.0, 20.0, 110.0, nin=0, ot=[""]),
            O("fr_unpk", "unpack f f f", 20.0, 52.0, 120.0, nin=1, nout=3,
              ot=["float", "float", "float"]),
            O("fr_stt", "t b f", 20.0, 86.0, 50.0, nin=1, nout=2, ot=["bang", "float"]),
            O("fr_fmt", "sprintf %g 0. %g %g", 20.0, 120.0, 180.0, nin=3, ot=[""]),
            O("fr_line", "line~", 20.0, 158.0, 60.0, nin=2, nout=2, ot=["signal", "bang"]),
            O("fr_play", "play~ ---rollBuf 2", 20.0, 196.0, 150.0, nin=1, nout=3,
              ot=["signal", "signal", "bang"]),
            O("fr_sL", "send~ ---renderL", 20.0, 234.0, 120.0, nin=1, nout=0),
            O("fr_sR", "send~ ---renderR", 150.0, 234.0, 120.0, nin=1, nout=0),
            # karma sequence: renderActive on -> stop -> record (+ start close timer)
            O("fr_ks", "t b b b", 220.0, 120.0, 80.0, nin=1, nout=3, ot=["bang"] * 3),
            M("fr_ra1", "1", 220.0, 156.0, 26.0),
            O("fr_ras", "s ---renderActive", 220.0, 184.0, 120.0, nout=0),
            M("fr_kstop", "stop", 300.0, 156.0, 44.0),
            M("fr_krec", "record", 350.0, 156.0, 60.0),
            O("fr_km", "s ---karmaMsg", 350.0, 320.0, 100.0, nout=0),
            O("fr_dl", "delay 100", 430.0, 156.0, 90.0, nin=2, ot=["bang"]),
            # close: renderActive off (speed->1, source->live) BEFORE play
            O("fr_cl", "t b b b b b", 430.0, 194.0, 110.0, nin=1, nout=5, ot=["bang"] * 5),
            M("fr_ra0", "0", 430.0, 230.0, 26.0),
            O("fr_ras2", "s ---renderActive", 430.0, 258.0, 120.0, nout=0),
            M("fr_kplay", "play", 490.0, 230.0, 44.0),
            M("fr_rgb", "bang", 550.0, 230.0, 44.0),
            O("fr_rg", "s ---regrid", 550.0, 258.0, 90.0, nout=0),
            M("fr_hc1", "1", 610.0, 230.0, 26.0),
            O("fr_hcs", "s ---hasContent", 610.0, 258.0, 110.0, nout=0),
            O("fr_dl2", "delay 25", 430.0, 286.0, 80.0, nin=2, ot=["bang"]),
            M("fr_pl0", "0", 430.0, 316.0, 26.0),
            O("fr_pls", "s ---prerollLoop", 430.0, 344.0, 110.0, nout=0),
            O("fr_rainit", "loadmess 0", 600.0, 20.0, 80.0, nin=1, ot=[""]),
            O("fr_rais", "s ---renderActive", 600.0, 48.0, 120.0, nout=0),
        ],
        "lines": [
            Ln("fr_go", 0, "fr_unpk", 0),
            # unpack fires right-to-left: renderMs (o2), end (o1), start (o0)
            Ln("fr_unpk", 2, "fr_fmt", 2), Ln("fr_unpk", 2, "fr_dl", 1),
            Ln("fr_unpk", 1, "fr_fmt", 1),
            Ln("fr_unpk", 0, "fr_stt", 0),
            # t b f -> f outlet first: build the position list; b outlet second:
            # run the karma sequence so `record` lands after play~ is positioned
            Ln("fr_stt", 1, "fr_fmt", 0),
            Ln("fr_stt", 0, "fr_ks", 0),
            Ln("fr_fmt", 0, "fr_line", 0),
            Ln("fr_line", 0, "fr_play", 0),
            Ln("fr_play", 0, "fr_sL", 0), Ln("fr_play", 1, "fr_sR", 0),
            # ks: o2 renderActive=1 (speed->8, rec source->play~), o1 stop, o0 record
            Ln("fr_ks", 2, "fr_ra1", 0), Ln("fr_ra1", 0, "fr_ras", 0),
            Ln("fr_ks", 1, "fr_kstop", 0), Ln("fr_kstop", 0, "fr_km", 0),
            Ln("fr_ks", 0, "fr_krec", 0), Ln("fr_krec", 0, "fr_km", 0),
            Ln("fr_ks", 0, "fr_dl", 0),
            Ln("fr_dl", 0, "fr_cl", 0),
            # cl: o4 renderActive=0 first, o3 play, o2 regrid, o1 hasContent, o0 -> bridge off
            Ln("fr_cl", 4, "fr_ra0", 0), Ln("fr_ra0", 0, "fr_ras2", 0),
            Ln("fr_cl", 3, "fr_kplay", 0), Ln("fr_kplay", 0, "fr_km", 0),
            Ln("fr_cl", 2, "fr_rgb", 0), Ln("fr_rgb", 0, "fr_rg", 0),
            Ln("fr_cl", 1, "fr_hc1", 0), Ln("fr_hc1", 0, "fr_hcs", 0),
            Ln("fr_cl", 0, "fr_dl2", 0),
            Ln("fr_dl2", 0, "fr_pl0", 0), Ln("fr_pl0", 0, "fr_pls", 0),
            Ln("fr_rainit", 0, "fr_rais", 0),
        ],
    }
    root["boxes"].append({"box": {
        "id": "p_fastrender", "maxclass": "newobj", "text": "p FastRender",
        "numinlets": 0, "numoutlets": 0, "patching_rect": [2600.0, 640.0, 90.0, 20.0],
        "patcher": fr,
    }})

    # ===================================================== p Playback
    drop(pb, lambda pl: pl["source"] == ["obj-7", 0] and pl["destination"] == ["obj-20", 2])
    drop(pb, lambda pl: pl["source"] == ["obj-34", 0] and pl["destination"] == ["obj-20", 0])
    drop(pb, lambda pl: pl["source"] == ["obj-29", 0] and pl["destination"] == ["obj-20", 1])
    pb["boxes"] += [
        O("fr_add", "+~", 40.0, 40.0, 40.0, nin=2, ot=SIG),
        O("fr_boost", "line~", 40.0, 12.0, 60.0, nin=2, nout=2, ot=["signal", "bang"]),
        O("fr_bra", "r ---renderActive", 200.0, 10.0, 120.0, nin=0, ot=[""]),
        O("fr_bsel", "sel 1 0", 200.0, 38.0, 60.0, nin=2, nout=3, ot=["bang", "bang", ""]),
        M("fr_b7", "7. 0", 200.0, 66.0, 40.0),
        M("fr_b0", "0. 0", 248.0, 66.0, 40.0),
        O("fr_ract", "+ 1", 360.0, 38.0, 40.0, nin=2, ot=[""]),
        O("fr_recL", "selector~ 2", 40.0, 104.0, 90.0, nin=3, nout=1, ot=SIG),
        O("fr_recR", "selector~ 2", 140.0, 104.0, 90.0, nin=3, nout=1, ot=SIG),
        O("fr_rvL", "receive~ ---renderL", 40.0, 74.0, 130.0, nin=0, nout=1, ot=SIG),
        O("fr_rvR", "receive~ ---renderR", 140.0, 74.0, 130.0, nin=0, nout=1, ot=SIG),
    ]
    pb["lines"] += [
        Ln("obj-7", 0, "fr_add", 0),
        Ln("fr_boost", 0, "fr_add", 1),
        Ln("fr_add", 0, "obj-20", 2),
        Ln("fr_bra", 0, "fr_bsel", 0),
        Ln("fr_bsel", 0, "fr_b7", 0),
        Ln("fr_bsel", 1, "fr_b0", 0),
        Ln("fr_b7", 0, "fr_boost", 0),
        Ln("fr_b0", 0, "fr_boost", 0),
        Ln("fr_bra", 0, "fr_ract", 0),
        Ln("obj-34", 0, "fr_recL", 1),
        Ln("fr_rvL", 0, "fr_recL", 2),
        Ln("fr_ract", 0, "fr_recL", 0),
        Ln("fr_recL", 0, "obj-20", 0),
        Ln("obj-29", 0, "fr_recR", 1),
        Ln("fr_rvR", 0, "fr_recR", 2),
        Ln("fr_ract", 0, "fr_recR", 0),
        Ln("fr_recR", 0, "obj-20", 1),
    ]

    # ===================================================== diag repoint (logic only)
    # ---rollWritePos is gone; point the two visible diag fields at the new signals.
    rootbx = {b.get("box", b)["id"]: b.get("box", b) for b in root["boxes"]}
    rootbx["dg_spd_r"]["text"] = "r ---rollFold"      # SPD field = bar-within-ring 0..N-1 (wraps)
    rootbx["dg_frc_r"]["text"] = "r ---rollEndMs"     # FRC field = grab end, ms into the ring

    # ------------------------------------------------------------- save + check
    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (base {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
