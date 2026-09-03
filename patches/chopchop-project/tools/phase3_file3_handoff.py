"""v6_186 -- Phase 3: LoopLength-bounded ring + the capture handoff.

Two coupled changes:

1. p Preroll's `record~ ---thisBuffer 2 @loop 1` now gets a loop END POINT =
   ---size (LoopLength ms) on inlet 3 and start 0 on inlet 2, so it wraps every
   LoopLength -- 0..LoopLength always holds the last contiguous LoopLength of
   input (v6_184/185 wrapped at the 120 s buffer end -> the "tail" rotation and
   stale content in the window). Re-sent on ring start and on LoopLength change.
   (record~ stereo inlet layout assumed: 0=L sig+ctrl, 1=R sig, 2=start ms,
   3=end ms. If wrong the ring behaviour will be off -- easy to move.)

2. On Record with the preroll FULL, divert instead of the normal clear+record:
   - `gate 2` on `record_trigger -> recordon_send`, control = ---prerollFull+1.
     full -> `s ---prerollCapture`; not full -> `s ---recordOn` (unchanged).
   - new `p PrerollCapture`: on `r ---prerollCapture` ->
       s ---prerollLoop 1
       s ---hasContent 1              (fires the size latch...)
       s ---capturedMs 120000        (...then overridden, last wins)
       s ---karmaMsg "set ---thisBuffer, position 0., window <---size/120000>, play"
       s ---regrid
     + keep-alive: `r ---sliceEdge` -> counter 0 15 -> carry -> gate(---prerollLoop)
       -> `jump 0.` -> s ---karmaMsg   (resets karma's phantom one-shot every
       LoopLength so the windowed loop never times out).
     `---prerollLoop` cleared by `r ---hasContent`==0 (INIT) and by `r ---recordOn`
     (a normal record).

No record pass, no `clear` -> the hiss/crackle phase is gone. Overlay still
frozen during a preroll loop (pos report dead) -- that's v6_187.

    python phase3_file3_handoff.py   # -> ../generated/ChopChop_v6_186.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_185.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_186.amxd"


def O(i, text, x, y, w=110, nin=2, nout=1, ot=None):
    return {"box": {"id": i, "maxclass": "newobj", "text": text, "numinlets": nin,
                    "numoutlets": nout, "outlettype": ot if ot is not None else [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


def M(i, text, x, y, w=110):
    return {"box": {"id": i, "maxclass": "message", "text": text, "numinlets": 2,
                    "numoutlets": 1, "outlettype": [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


def IN(i, x, y):
    return {"box": {"id": i, "maxclass": "inlet", "numinlets": 0, "numoutlets": 1,
                    "outlettype": ["signal"], "patching_rect": [float(x), float(y), 30.0, 30.0]}}


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


# --------------------------------------------------- rebuilt p Preroll (with end pt)
def preroll_patcher():
    B = [
        IN("p_l", 20, 20), IN("p_r", 70, 20),
        O("pr_rec", "record~ ---thisBuffer 2 @loop 1", 20, 100, 210, nin=4, nout=1, ot=["signal"]),
        M("pr_startpt", "0", 20, 70, 26),                       # -> inlet 2 (start ms)
        O("pr_endptf", "f", 120, 70, 30),                       # -> inlet 3 (end ms) = ---size

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

        O("pr_settle", "delay 400", 300, 278, 70, nin=2, nout=1, ot=["bang"]),
        O("pr_startt", "t b b b", 300, 300, 54, nin=1, nout=3, ot=["bang", "bang", "bang"]),
        M("pr_start", "reset, 1", 300, 326, 70),
        M("pr_stop", "0", 400, 326, 26),
        M("pr_settlestop", "stop", 380, 278, 44),

        O("pr_run1", "1", 470, 278, 26, nin=2, nout=1),
        O("pr_run0", "0", 500, 278, 26, nin=2, nout=1),
        O("pr_running", "f 0", 470, 306, 40),

        O("pr_ronsel", "sel 1", 620, 46, 44, nin=2, nout=2, ot=["bang", ""]),
        M("pr_ronstop", "0", 620, 72, 26),

        O("pr_lddel", "delay 4000", 300, 380, 80, nin=2, nout=1, ot=["bang"]),
        M("pr_ldstop", "stop", 400, 380, 44),
        M("pr_full1", "1", 300, 420, 26),
        M("pr_full0", "0", 340, 420, 26),
        O("pr_fulls", "s ---prerollFull", 300, 448, 120, nin=1, nout=0),

        O("pr_sizech", "change", 560, 110, 50),
        O("pr_szt", "t b b i", 560, 138, 54, nin=1, nout=3, ot=["bang", "bang", "int"]),
        O("pr_szgate", "gate 1", 560, 166, 54, nin=2, nout=1),
        M("pr_szreset", "reset", 560, 196, 50),
    ]
    L = [
        Ln("p_l", 0, "pr_rec", 0), Ln("p_r", 0, "pr_rec", 1),
        Ln("pr_startpt", 0, "pr_rec", 2),
        Ln("pr_size", 0, "pr_endptf", 0), Ln("pr_endptf", 0, "pr_rec", 3),

        Ln("pr_arm", 0, "pr_at", 0),
        Ln("pr_at", 1, "pr_hf", 0), Ln("pr_at", 0, "pr_af", 0),
        Ln("pr_hc", 0, "pr_ht", 0),
        Ln("pr_ht", 1, "pr_hf", 0), Ln("pr_ht", 0, "pr_af", 0),
        Ln("pr_hf", 0, "pr_hfinv", 0), Ln("pr_hfinv", 0, "pr_want", 1),
        Ln("pr_af", 0, "pr_want", 0),
        Ln("pr_want", 0, "pr_wantch", 0), Ln("pr_wantch", 0, "pr_wsel", 0),

        Ln("pr_wsel", 0, "pr_settle", 0),
        Ln("pr_settle", 0, "pr_startt", 0),
        Ln("pr_startt", 2, "pr_startpt", 0),      # start ms 0 (first)
        Ln("pr_startt", 1, "pr_endptf", 0),       # bang end pt = ---size
        Ln("pr_startt", 0, "pr_start", 0),         # reset, 1 (last)
        Ln("pr_start", 0, "pr_rec", 0),
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

        Ln("pr_size", 0, "pr_sizech", 0),
        Ln("pr_sizech", 0, "pr_szt", 0),
        Ln("pr_szt", 2, "pr_lddel", 1),
        Ln("pr_szt", 1, "pr_endptf", 0),          # update record~ end pt
        Ln("pr_szt", 0, "pr_szgate", 1),
        Ln("pr_running", 0, "pr_szgate", 0),
        Ln("pr_szgate", 0, "pr_szreset", 0), Ln("pr_szreset", 0, "pr_rec", 0),
        Ln("pr_szgate", 0, "pr_lddel", 0),
        Ln("pr_szgate", 0, "pr_full0", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 900.0, 660.0],
            "boxes": B, "lines": L}


# --------------------------------------------------------------- p PrerollCapture
def prcap_patcher():
    B = [
        O("pc_trig", "r ---prerollCapture", 20, 20, 140, nin=0, nout=1),
        O("pc_sizer", "r ---size", 300, 20, 90, nin=0, nout=1),
        O("pc_frac", "/ 120000.", 300, 46, 70),
        O("pc_fracf", "f", 300, 72, 30),
        M("pc_msg", "set ---thisBuffer, position 0., window $1, play", 20, 200, 300),
        O("pc_kmsg", "s ---karmaMsg", 20, 228, 110, nin=1, nout=0),

        O("pc_t", "t b b b b b", 20, 60, 90, nin=1, nout=5,
          ot=["bang", "bang", "bang", "bang", "bang"]),
        M("pc_pl1", "1", 20, 92, 26), O("pc_pls", "s ---prerollLoop", 60, 92, 120, nin=1, nout=0),
        M("pc_hc1", "1", 20, 118, 26), O("pc_hcs", "s ---hasContent", 60, 118, 120, nin=1, nout=0),
        M("pc_cap", "120000", 20, 144, 60), O("pc_caps", "s ---capturedMs", 90, 144, 120, nin=1, nout=0),
        O("pc_endt", "t b b", 20, 172, 44, nin=1, nout=2, ot=["bang", "bang"]),
        M("pc_rg", "bang", 240, 200, 40), O("pc_rgs", "s ---regrid", 240, 228, 90, nin=1, nout=0),

        # keep-alive
        O("pc_se", "r ---sliceEdge", 420, 60, 110, nin=0, nout=1),
        O("pc_cnt", "counter 0 15", 420, 86, 90, nin=5, nout=4, ot=["int", "int", "int", "int"]),
        O("pc_kag", "gate 1", 420, 114, 54, nin=2, nout=1),
        O("pc_plr", "r ---prerollLoop", 560, 60, 120, nin=0, nout=1),
        M("pc_jm", "jump 0.", 420, 142, 60),
        O("pc_jms", "s ---karmaMsg", 420, 170, 110, nin=1, nout=0),

        # ---prerollLoop clears
        O("pc_hcr", "r ---hasContent", 640, 100, 120, nin=0, nout=1),
        O("pc_hcsel", "sel 0", 640, 126, 44, nin=2, nout=2, ot=["bang", ""]),
        O("pc_ronr", "r ---recordOn", 780, 100, 110, nin=0, nout=1),
        M("pc_pl0", "0", 700, 152, 26), O("pc_pls2", "s ---prerollLoop", 700, 178, 120, nin=1, nout=0),
    ]
    L = [
        Ln("pc_trig", 0, "pc_t", 0),
        Ln("pc_sizer", 0, "pc_frac", 0), Ln("pc_frac", 0, "pc_fracf", 0),
        Ln("pc_t", 4, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),     # 1st: prerollLoop 1
        Ln("pc_t", 3, "pc_fracf", 0),                                 # 2nd: refresh $1
        Ln("pc_t", 2, "pc_hc1", 0), Ln("pc_hc1", 0, "pc_hcs", 0),     # 3rd: hasContent 1
        Ln("pc_t", 1, "pc_cap", 0), Ln("pc_cap", 0, "pc_caps", 0),    # 4th: capturedMs 120000 (override)
        Ln("pc_t", 0, "pc_endt", 0),                                  # 5th (last):
        Ln("pc_endt", 1, "pc_msg", 0), Ln("pc_msg", 0, "pc_kmsg", 0), #   karma set/window/play
        Ln("pc_endt", 0, "pc_rg", 0), Ln("pc_rg", 0, "pc_rgs", 0),    #   then regrid
        Ln("pc_fracf", 0, "pc_msg", 1),

        Ln("pc_se", 0, "pc_cnt", 0),
        Ln("pc_cnt", 2, "pc_kag", 1),           # carry flag -> gate data
        Ln("pc_plr", 0, "pc_kag", 0),           # gate open only while in a preroll loop
        Ln("pc_kag", 0, "pc_jm", 0), Ln("pc_jm", 0, "pc_jms", 0),

        Ln("pc_hcr", 0, "pc_hcsel", 0),
        Ln("pc_hcsel", 0, "pc_pl0", 0),         # hasContent 0 (INIT) -> prerollLoop 0
        Ln("pc_ronr", 0, "pc_pl0", 0),          # normal record -> prerollLoop 0
        Ln("pc_pl0", 0, "pc_pls2", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 950.0, 320.0],
            "boxes": B, "lines": L}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    ids = {b.get("box", b)["id"] for b in root["boxes"]}
    assert "obj-18" in ids and "recordon_send" in ids

    # 1) rebuild p Preroll
    pbox = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_preroll")
    pbox["patcher"] = preroll_patcher()

    # 2) divert gate on record_trigger -> recordon_send
    before = len(root["lines"])
    root["lines"] = [e for e in root["lines"]
                     if not (e.get("patchline", e)["source"][:2] == ["obj-18", 0]
                             and e.get("patchline", e)["destination"][:2] == ["recordon_send", 0])]
    assert before - len(root["lines"]) == 1, "record_trigger->recordon_send cord not found"

    root["boxes"] += [
        O("rc_gate", "gate 2", 640.0, 250.0, 54, nin=2, nout=2, ot=["", ""]),
        O("rc_gctl", "r ---prerollFull", 640.0, 220.0, 120, nin=0, nout=1),
        O("rc_gadd", "+ 1", 640.0, 236.0, 34),
        O("rc_pcs", "s ---prerollCapture", 720.0, 285.0, 130, nin=1, nout=0),
        {"box": {"id": "p_prcap", "maxclass": "newobj", "text": "p PrerollCapture",
                 "numinlets": 0, "numoutlets": 0, "patching_rect": [2600.0, 560.0, 110.0, 22.0],
                 "patcher": prcap_patcher()}},
    ]
    root["lines"] += [
        Ln("rc_gctl", 0, "rc_gadd", 0), Ln("rc_gadd", 0, "rc_gate", 0),
        Ln("obj-18", 0, "rc_gate", 1),
        Ln("rc_gate", 0, "recordon_send", 0),      # not full -> normal
        Ln("rc_gate", 1, "rc_pcs", 0),             # full -> preroll capture
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
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
