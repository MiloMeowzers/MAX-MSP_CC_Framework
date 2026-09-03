"""v6_185 -- Phase 3 file 2: rewrite p Preroll's state machine for reliability.

v6_184 problems (user-reported: repeated full INIT -> compressed slices / wrong
lengths / fragments):
  1. the ring's record~ only stopped on ---hasContent -> 1 (end of the record
     pass), so during a normal capture record~ and karma wrote ---thisBuffer at
     the same time -> corruption.
  2. `pr_run` (a `change`) got stuck at 1 after a capture->INIT cycle -> the ring
     never cleanly restarted.
  3. the ring restarted the instant ---hasContent -> 0, racing the INIT's
     clear / regrid / stop / window / position.

Rewrite (full replace of p Preroll's inner patcher; it is a box added in v6_184,
not round-tripped, so this is clean):
  - want = arm AND (hasContent == 0), recomputed correctly on either input via
    t i b / t b i ordering; `change` on `want` only guards redundant edges, and
    `want` genuinely goes 0 then 1 across a capture->INIT cycle so it never
    sticks.
  - `r ---recordOn` -> sel 1 -> immediate `0` to record~  (stop before any
    capture writes the buffer).
  - want -> 1 goes through `delay 400` before `reset, 1` -> record~  (settle;
    repeated INITs keep pushing it out).
  - `pr_running` flag gates the LoopLength-change restart.

    python phase3_file2_preroll_statemachine.py   # -> ../generated/ChopChop_v6_185.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_184.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_185.amxd"


def O(i, text, x, y, w=110, nin=2, nout=1, ot=None):
    return {"box": {"id": i, "maxclass": "newobj", "text": text, "numinlets": nin,
                    "numoutlets": nout, "outlettype": ot if ot is not None else [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


def M(i, text, x, y, w=80):
    return {"box": {"id": i, "maxclass": "message", "text": text, "numinlets": 2,
                    "numoutlets": 1, "outlettype": [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


def IN(i, x, y):
    return {"box": {"id": i, "maxclass": "inlet", "numinlets": 0, "numoutlets": 1,
                    "outlettype": ["signal"], "patching_rect": [float(x), float(y), 30.0, 30.0]}}


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def preroll_patcher():
    B = [
        IN("p_l", 20, 20), IN("p_r", 70, 20),
        O("pr_rec", "record~ ---thisBuffer 2 @loop 1", 20, 90, 210, nin=3, nout=1, ot=["signal"]),

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

        O("pr_sizech", "change", 560, 110, 50),
        O("pr_szt", "t b i", 560, 138, 44, nin=1, nout=2, ot=["bang", "int"]),
        O("pr_szgate", "gate 1", 560, 166, 54, nin=2, nout=1),
        M("pr_szreset", "reset", 560, 196, 50),
    ]
    L = [
        Ln("p_l", 0, "pr_rec", 0), Ln("p_r", 0, "pr_rec", 1),

        # want = arm AND (hc == 0)
        Ln("pr_arm", 0, "pr_at", 0),
        Ln("pr_at", 1, "pr_hf", 0),      # b (first): re-emit hc -> hfinv -> want cold
        Ln("pr_at", 0, "pr_af", 0),      # i (second): store+emit arm -> want hot -> compute
        Ln("pr_hc", 0, "pr_ht", 0),
        Ln("pr_ht", 1, "pr_hf", 0),      # i (first): store+emit hc -> hfinv -> want cold
        Ln("pr_ht", 0, "pr_af", 0),      # b (second): re-emit arm -> want hot -> compute
        Ln("pr_hf", 0, "pr_hfinv", 0),
        Ln("pr_hfinv", 0, "pr_want", 1),
        Ln("pr_af", 0, "pr_want", 0),
        Ln("pr_want", 0, "pr_wantch", 0),
        Ln("pr_wantch", 0, "pr_wsel", 0),

        # want -> 1 : settle then start
        Ln("pr_wsel", 0, "pr_settle", 0),
        Ln("pr_settle", 0, "pr_start", 0), Ln("pr_start", 0, "pr_rec", 0),
        Ln("pr_settle", 0, "pr_run1", 0), Ln("pr_run1", 0, "pr_running", 0),
        Ln("pr_settle", 0, "pr_lddel", 0),          # start LED delay only once the ring is really running
        # want -> 0 : stop now
        Ln("pr_wsel", 1, "pr_stop", 0), Ln("pr_stop", 0, "pr_rec", 0),
        Ln("pr_wsel", 1, "pr_settlestop", 0), Ln("pr_settlestop", 0, "pr_settle", 0),
        Ln("pr_wsel", 1, "pr_run0", 0), Ln("pr_run0", 0, "pr_running", 0),
        Ln("pr_wsel", 1, "pr_ldstop", 0), Ln("pr_ldstop", 0, "pr_lddel", 0),
        Ln("pr_wsel", 1, "pr_full0", 0),

        # record START -> stop the ring immediately (before it can fight karma)
        Ln("pr_ron", 0, "pr_ronsel", 0),
        Ln("pr_ronsel", 0, "pr_ronstop", 0), Ln("pr_ronstop", 0, "pr_rec", 0),
        Ln("pr_ronsel", 0, "pr_settlestop", 0),
        Ln("pr_ronsel", 0, "pr_run0", 0),
        Ln("pr_ronsel", 0, "pr_ldstop", 0),

        # LED delay
        Ln("pr_size", 0, "pr_lddel", 1),
        Ln("pr_lddel", 0, "pr_full1", 0),
        Ln("pr_full1", 0, "pr_fulls", 0), Ln("pr_full0", 0, "pr_fulls", 0),

        # LoopLength change -> if running, reset ring + restart LED delay
        Ln("pr_size", 0, "pr_sizech", 0),
        Ln("pr_sizech", 0, "pr_szt", 0),
        Ln("pr_szt", 1, "pr_lddel", 1),
        Ln("pr_szt", 0, "pr_szgate", 1),
        Ln("pr_running", 0, "pr_szgate", 0),
        Ln("pr_szgate", 0, "pr_szreset", 0), Ln("pr_szreset", 0, "pr_rec", 0),
        Ln("pr_szgate", 0, "pr_lddel", 0),
        Ln("pr_szgate", 0, "pr_full0", 0),
    ]
    return {
        "fileversion": 1,
        "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
        "classnamespace": "box",
        "rect": [40.0, 40.0, 900.0, 640.0],
        "boxes": B, "lines": L,
    }


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    pbox = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_preroll")
    old = len(pbox["patcher"]["boxes"]), len(pbox["patcher"]["lines"])
    pbox["patcher"] = preroll_patcher()
    new = len(pbox["patcher"]["boxes"]), len(pbox["patcher"]["lines"])
    print(f"p Preroll: {old} -> {new} (boxes, lines)")

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
