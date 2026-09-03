"""v6_202 -- Phase 5 file 1: the rolling substrate (spec: context.md "Phase 5/6 design").

Decouples the roll cadence from the master length. A continuous ring records the input mix
the whole time the device is armed; a fixed 1-bar transport-locked cadence marks commit
points; Commit grabs the last <LoopLength> ending at the most recent bar mark and plays it
through the v6_201 groove~ engine. No master / slice change yet -- this is the foundation
v6_203 (fast-render Commit into karmaMaster) sits on.

 new  buffer~ ---rollBuf 120000 2                       (in p Playback/p BufferSwitching)

 new  p RollCapture  (root subpatcher, 2 audio inlets):
   rc_rec   record~ ---rollBuf 2 @loop 1                continuous ring
   rc_arm   r ---prerollArm -> sel 1 0                  1 = reset + start, 0 = stop
   rc_ph    phasor~ @frequency 1n @lock 1 -> delta~ -> <~ 0. -> edge~   1-bar cadence
   rc_cnt   counter (bar marks) -> s ---dbgBar
   rc_snap  snapshot~  <- rc_rec sync outlet, banged by the bar edge
            -> * 120000. -> s ---rollWritePos                ring write pos in ms at the mark

 p Preroll: cut p_l/p_r -> pr_rec so it no longer writes ---thisBuffer (the FULL-LED /
   ---prerollFull "armed long enough" logic is left intact).

 p PrerollCapture: groove~ now grabs from ---rollBuf, region = [writePos - ---size, writePos]:
   pc_setb  "set ---rollBuf"                             (was set ---thisBuffer)
   pc_seq[5] -> pc_szf (f, <- r ---size) -> pc_ssub cold
   pc_seq[4] -> pc_wef (f, <- r ---rollWritePos) -> pc_le (s ---gvLoopEnd)
                                              and -> pc_ssub hot
   pc_ssub (-) -> pc_swrap  expr ($f1<0.)?($f1+120000.):$f1  -> pc_lss (s ---gvLoopStart)
   (pc_ls "0" removed)

 diag repoint (logic only, no layout change -- both fields were obsolete under groove~):
   dg_spd_r : "r ---dbgSpeed"  -> "r ---dbgBar"        SPD field now shows the bar counter
   dg_frc_r : "r ---windowVal" -> "r ---rollWritePos"  FRC field now shows ring write pos (ms)

    python phase3_file19_rolling_substrate.py   # -> ../generated/ChopChop_v6_202.amxd
"""
from pathlib import Path
import copy

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_201.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_202.amxd"


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


def inlet(bid, idx, x, sig=True):
    return {"box": {"comment": "", "id": bid, "index": idx, "maxclass": "inlet",
                    "numinlets": 0, "numoutlets": 1,
                    "outlettype": ["signal" if sig else ""],
                    "patching_rect": [x, 20.0, 30.0, 30.0]}}


def drop_line(pat, s, d):
    pat["lines"] = [e for e in pat["lines"]
                    if not (e.get("patchline", e)["source"][0] == s
                            and e.get("patchline", e)["destination"][0] == d)]


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    rootbx = {b.get("box", b)["id"]: b.get("box", b) for b in root["boxes"]}

    pb = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "obj-118")["patcher"]
    pc = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_prcap")["patcher"]
    pr = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_preroll")["patcher"]
    bsw = next(b.get("box", b) for b in pb["boxes"] if b.get("box", b)["id"] == "obj-59")["patcher"]

    SIG = ["signal"]

    # ---------------------------------------------------------------- buffer~ ---rollBuf
    bsw["boxes"].append(nobj("rollbuf", "buffer~ ---rollBuf 120000 2", 40.0, 320.0, 190.0,
                             nin=1, nout=2, outtype=["signal", "bang"]))

    # ---------------------------------------------------------------- p RollCapture subpatcher
    inner = {
        "fileversion": 1,
        "appversion": copy.deepcopy(root.get("appversion", {"major": 9, "minor": 1, "revision": 4})),
        "classnamespace": "box",
        "rect": [0.0, 0.0, 640.0, 480.0],
        "boxes": [
            inlet("rcp_l", 1, 20.0), inlet("rcp_r", 2, 60.0),
            nobj("rc_rec", "record~ ---rollBuf 2 @loop 1", 20.0, 120.0, 210.0, nin=4, nout=1, outtype=SIG),
            nobj("rc_arm", "r ---prerollArm", 300.0, 40.0, 100.0, nin=0, outtype=[""]),
            nobj("rc_armsel", "sel 1 0", 300.0, 72.0, 60.0, nin=2, nout=3, outtype=["bang", "bang", ""]),
            nmsg("rc_on", "1", 300.0, 104.0, 26.0),
            nmsg("rc_rst", "reset", 332.0, 104.0, 44.0),
            nmsg("rc_off", "0", 382.0, 104.0, 26.0),
            nobj("rc_ph", "phasor~ @frequency 1n @lock 1", 20.0, 200.0, 180.0, nin=1, nout=1, outtype=SIG),
            nobj("rc_dl", "delta~", 20.0, 232.0, 50.0, nin=1, nout=1, outtype=SIG),
            nobj("rc_lt", "<~ 0.", 20.0, 264.0, 44.0, nin=2, nout=1, outtype=SIG),
            nobj("rc_edge", "edge~", 20.0, 296.0, 44.0, nin=1, nout=2, outtype=["bang", "bang"]),
            nobj("rc_cnt", "counter", 20.0, 336.0, 60.0, nin=5, nout=4, outtype=["int", "", "", "int"]),
            nobj("rc_bars", "s ---dbgBar", 20.0, 368.0, 90.0, nout=0),
            nobj("rc_snap", "snapshot~", 140.0, 336.0, 70.0, nin=1, nout=1, outtype=[""]),
            nobj("rc_posms", "* 120000.", 140.0, 368.0, 70.0, nin=2, nout=1, outtype=[""]),
            nobj("rc_poss", "s ---rollWritePos", 140.0, 400.0, 120.0, nout=0),
        ],
        "lines": [
            Ln("rcp_l", 0, "rc_rec", 0), Ln("rcp_r", 0, "rc_rec", 1),
            Ln("rc_arm", 0, "rc_armsel", 0),
            Ln("rc_armsel", 0, "rc_rst", 0), Ln("rc_armsel", 0, "rc_on", 0),
            Ln("rc_armsel", 1, "rc_off", 0),
            Ln("rc_rst", 0, "rc_rec", 0), Ln("rc_on", 0, "rc_rec", 0), Ln("rc_off", 0, "rc_rec", 0),
            Ln("rc_ph", 0, "rc_dl", 0), Ln("rc_dl", 0, "rc_lt", 0), Ln("rc_lt", 0, "rc_edge", 0),
            Ln("rc_edge", 0, "rc_cnt", 0), Ln("rc_cnt", 0, "rc_bars", 0),
            Ln("rc_rec", 0, "rc_snap", 0), Ln("rc_edge", 0, "rc_snap", 0),
            Ln("rc_snap", 0, "rc_posms", 0), Ln("rc_posms", 0, "rc_poss", 0),
        ],
    }
    root["boxes"].append({"box": {
        "id": "p_rollcap", "maxclass": "newobj", "text": "p RollCapture",
        "numinlets": 2, "numoutlets": 0, "patching_rect": [2600.0, 560.0, 90.0, 20.0],
        "patcher": inner,
    }})
    root["lines"] += [Ln("ingain_L", 0, "p_rollcap", 0), Ln("ingain_R", 0, "p_rollcap", 1)]

    # ---------------------------------------------------------------- p Preroll: stop writing ---thisBuffer
    drop_line(pr, "p_l", "pr_rec")
    drop_line(pr, "p_r", "pr_rec")

    # ---------------------------------------------------------------- p PrerollCapture: grab from ---rollBuf
    pcbx = {b.get("box", b)["id"]: b.get("box", b) for b in pc["boxes"]}
    pcbx["pc_setb"]["text"] = "set ---rollBuf"
    # remove pc_ls ("0" -> pc_lss)
    pc["boxes"] = [b for b in pc["boxes"] if b.get("box", b)["id"] != "pc_ls"]
    pc["lines"] = [e for e in pc["lines"]
                   if e.get("patchline", e)["source"][0] != "pc_ls"
                   and e.get("patchline", e)["destination"][0] != "pc_ls"]
    # pc_szf no longer feeds pc_le; it feeds the subtract's cold inlet
    drop_line(pc, "pc_szf", "pc_le")
    pc["boxes"] += [
        nobj("pc_we", "r ---rollWritePos", 200.0, 40.0, 120.0, nin=0, outtype=[""]),
        nobj("pc_wef", "f", 200.0, 72.0, 40.0, nin=2, outtype=[""]),
        nobj("pc_ssub", "-", 120.0, 190.0, 40.0, nin=2, outtype=[""]),
        nobj("pc_swrap", "expr ($f1<0.)?($f1+120000.):$f1", 120.0, 222.0, 200.0, nin=1, outtype=[""]),
    ]
    pc["lines"] += [
        Ln("pc_we", 0, "pc_wef", 1),
        Ln("pc_seq", 4, "pc_wef", 0),
        Ln("pc_wef", 0, "pc_le", 0),
        Ln("pc_wef", 0, "pc_ssub", 0),
        Ln("pc_szf", 0, "pc_ssub", 1),
        Ln("pc_ssub", 0, "pc_swrap", 0),
        Ln("pc_swrap", 0, "pc_lss", 0),
    ]

    # ---------------------------------------------------------------- diag repoint (logic only)
    rootbx["dg_spd_r"]["text"] = "r ---dbgBar"
    rootbx["dg_frc_r"]["text"] = "r ---rollWritePos"

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
