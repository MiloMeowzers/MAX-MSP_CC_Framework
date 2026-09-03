"""v6_187 -- fix the v6_186 handoff (no audio / no playstate on Record).

Causes:
 1. `rc_gate` was `gate 2` = CLOSED by default, so a Record click before
    ---prerollFull ever fired went nowhere (neither ---recordOn nor
    ---prerollCapture).
 2. record~ start/end-point inlets 2/3 were an unverified assumption -- the extra
    cords may have disturbed the ring. Reverted to a plain 2-inlet
    `record~ ---thisBuffer 2 @loop 1` (wraps at 120 s again -> rotated capture,
    functional; proper LoopLength bounding deferred until the inlet layout is
    confirmed).
 3. `pc_fracf` had no default -> if ---size hadn't reached p PrerollCapture,
    `window $1` -> `window 0` -> silence. Now `f 0.0667` (~4 bar / 120 s).

Changes: `rc_gate` -> `gate 2 1` + loadbang `1 -> rc_gate` control; drop
`pr_startpt` / `pr_endptf` and the inlet-2/3 cords, `pr_rec` back to 2 inlets;
`pc_fracf` -> `f 0.0667`.

    python phase3_file4_handoff_fixes.py   # -> ../generated/ChopChop_v6_187.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_186.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_187.amxd"


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher

    # --- 1. rc_gate -> gate 2 1  + loadbang open ---
    rcg = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "rc_gate")
    assert rcg["text"] == "gate 2", rcg["text"]
    rcg["text"] = "gate 2 1"
    ids = {b.get("box", b)["id"] for b in root["boxes"]}
    assert "rc_lb" not in ids and "rc_lb1" not in ids
    root["boxes"] += [
        {"box": {"id": "rc_lb", "maxclass": "newobj", "text": "loadbang", "numinlets": 1,
                 "numoutlets": 1, "outlettype": ["bang"], "patching_rect": [560.0, 205.0, 60.0, 20.0]}},
        {"box": {"id": "rc_lb1", "maxclass": "message", "text": "1", "numinlets": 2, "numoutlets": 1,
                 "outlettype": [""], "patching_rect": [560.0, 228.0, 26.0, 20.0]}},
    ]
    root["lines"] += [Ln("rc_lb", 0, "rc_lb1", 0), Ln("rc_lb1", 0, "rc_gate", 0)]

    # --- 2. p Preroll: drop start/end-point boxes, pr_rec back to 2 inlets ---
    pbox = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_preroll")
    pp = pbox["patcher"]
    drop = {"pr_startpt", "pr_endptf"}
    pp["boxes"] = [b for b in pp["boxes"] if b.get("box", b)["id"] not in drop]
    for b in pp["boxes"]:
        bb = b.get("box", b)
        if bb["id"] == "pr_rec":
            assert bb["text"] == "record~ ---thisBuffer 2 @loop 1"
            bb["numinlets"] = 2

    def keep(e):
        pl = e.get("patchline", e)
        s, d = pl["source"], pl["destination"]
        if s[0] in drop or d[0] in drop:
            return False
        if d[0] == "pr_rec" and d[1] in (2, 3):   # any stray cords to the removed inlets
            return False
        return True
    before = len(pp["lines"])
    pp["lines"] = [e for e in pp["lines"] if keep(e)]
    print(f"p Preroll lines {before} -> {len(pp['lines'])} (removed start/end-point wiring)")

    # --- 3. pc_fracf default ---
    pcap = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_prcap")
    for b in pcap["patcher"]["boxes"]:
        bb = b.get("box", b)
        if bb["id"] == "pc_fracf":
            assert bb["text"] == "f"
            bb["text"] = "f 0.0667"

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    for p, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {p} {d}")
    e = find_scope(load(OUT).patcher, "/")
    rg = e.boxes["rc_gate"]
    print("rc_gate:", rg["text"], " control feeders:",
          [(s, so) for (s, so, d, di) in e.lines() if d == "rc_gate" and di == 0])
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
