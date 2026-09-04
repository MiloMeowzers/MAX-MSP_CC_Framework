"""v6_208 -- Phase 5 file 7: v6_203 minus the auto-commit, plus the reinit.

Base **v6_203** (the file the user confirms has a working fast render -- the
full loop plays; the auto-commit thrash is what wrecks it).  This is the
minimal change the user asked for: strip ONLY the timer-driven auto-commit
cluster from `p PrerollCapture`, add the `report 20`/`snramp 16`/`ramp 16`
reinit to `p FastRender` (the "wire it into everything else" for the chase
overlay).  The render mechanism -- `play~ ---rollBuf` + `line~` position ramp,
the `+~` speed boost (obj-7 + 7), `renderMs = pc_rmsx = sizeMs/8` -- is
UNTOUCHED, as is the wrap router (`pc_wrapx`/`pc_wsel`/`pc_gate`) and every
other expr.

p PrerollCapture
  remove 12 boxes: pc_full pc_fsel pc_hcr pc_hcinv pc_fgate pc_fpend pc_fpf
                   pc_fbarr pc_fbang pc_fchk pc_fclr pc_fcs
  and every line touching them (incl. pc_gate[1] -> pc_fpend, the defer arm).
  -> the manual Record path (rc_gate on ---prerollFull -> ---prerollCapture ->
     pc_trig) is the only Commit trigger.  A grab that would wrap routes to
     pc_gate outlet 1 -> nowhere (Commit dropped; press Record again next bar).

p FastRender
  + fr_reit (t b b b) off fr_cl[2] (alongside the regrid bang) ->
    fr_rep "report 20" / fr_snr "snramp 16" / fr_rmp "ramp 16" -> s ---karmaMsg
    (fires right after `play`, matching the normal ---recordOn reinit).

Known-not-fixed here: the slight tempo error (loop length = renderMs *
(obj-7 + 7); exact only when obj-7 == 1).  That is the next build, isolated.

    python phase3_file25_v203_minus_autocommit.py   # -> ../generated/ChopChop_v6_208.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_203.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_208.amxd"

AUTO = {"pc_full", "pc_fsel", "pc_hcr", "pc_hcinv", "pc_fgate", "pc_fpend",
        "pc_fpf", "pc_fbarr", "pc_fbang", "pc_fchk", "pc_fclr", "pc_fcs"}


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def O(bid, text, x, y, w=90.0, nin=1, nout=1, ot=None):
    b = {"id": bid, "maxclass": "newobj", "text": text, "numinlets": nin,
         "numoutlets": nout, "patching_rect": [float(x), float(y), float(w), 22.0]}
    if ot is not None:
        b["outlettype"] = ot
    return {"box": b}


def M(bid, text, x, y, w=70.0):
    return {"box": {"id": bid, "maxclass": "message", "text": text, "numinlets": 2,
                    "numoutlets": 1, "outlettype": [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


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

    pc = find(root, lambda x: x.get("text") == "p PrerollCapture")["patcher"]
    fr = find(root, lambda x: x.get("text") == "p FastRender")["patcher"]

    # -------- p PrerollCapture: strip the auto-commit cluster only
    n0 = len(pc["boxes"])
    pc["boxes"] = [b for b in pc["boxes"] if b.get("box", b)["id"] not in AUTO]
    removed = n0 - len(pc["boxes"])
    assert removed == len(AUTO), f"removed {removed} of {len(AUTO)} auto boxes"
    pc["lines"] = [e for e in pc["lines"]
                   if e.get("patchline", e)["source"][0] not in AUTO
                   and e.get("patchline", e)["destination"][0] not in AUTO]

    # -------- p FastRender: add the reinit off fr_cl[2]
    fr["boxes"] += [
        O("fr_reit", "t b b b", 470.0, 300.0, 80.0, nin=1, nout=3, ot=["bang"] * 3),
        M("fr_rep", "report 20", 470.0, 332.0, 70.0),
        M("fr_snr", "snramp 16", 550.0, 332.0, 80.0),
        M("fr_rmp", "ramp 16", 630.0, 332.0, 70.0),
    ]
    fr["lines"] += [
        Ln("fr_cl", 2, "fr_reit", 0),
        Ln("fr_reit", 2, "fr_rep", 0),
        Ln("fr_reit", 1, "fr_snr", 0),
        Ln("fr_reit", 0, "fr_rmp", 0),
        Ln("fr_rep", 0, "fr_km", 0),
        Ln("fr_snr", 0, "fr_km", 0),
        Ln("fr_rmp", 0, "fr_km", 0),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_203 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
