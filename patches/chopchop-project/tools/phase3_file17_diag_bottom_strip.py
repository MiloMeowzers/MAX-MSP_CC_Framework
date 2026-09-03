"""v6_200 -- give the device a visible diag strip along a new bottom row.

The M4L device presentation is `openrect [0,0,0,169]` -- ~169 px tall, and
Live cuts the width off before x1130. Every diag box I placed (x1130, y168+)
was off both edges. That's the whole "can't see SPD/RON / MAN is buried"
problem.

 - openrect -> [0, 0, 940, 250]  (explicit width 940, height 250 -> a clear
   ~80 px strip below the existing content).
 - A dark `panel` behind the strip (pres [0, 168, 940, 82]).
 - All diag values in ONE horizontal row at y ~192: PLY FRC HC FUL SIZ CAP HND
   SPD RON, 100 px apart from x 12, each 60 wide, label at y 176.
 - MAN button + label at x ~900.

Handoff unchanged (v6_197 bare message).

    python phase3_file17_diag_bottom_strip.py   # -> ../generated/ChopChop_v6_200.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

ORANGE = [1.0, 0.709803921568627, 0.196078431372549, 1.0]

ROWS = ["dg_ply", "dg_frc", "dg_hc", "dg_ful", "dg_siz", "dg_cap", "dg_hnd", "dg_spd", "dg_ron"]

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_199.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_200.amxd"


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    root["openrect"] = [0.0, 0.0, 940.0, 250.0]

    bx = {b.get("box", b)["id"]: b.get("box", b) for b in root["boxes"]}

    # background panel for the strip
    if "dg_bg" not in bx:
        root["boxes"].insert(0, {"box": {
            "id": "dg_bg", "maxclass": "panel", "numinlets": 1, "numoutlets": 0,
            "mode": 0, "background": 1,
            "patching_rect": [2400.0, 400.0, 940.0, 82.0],
            "presentation": 1, "presentation_rect": [0.0, 168.0, 940.0, 82.0],
            "bgfillcolor": {"color1": [0.12, 0.12, 0.13, 1.0], "color": [0.12, 0.12, 0.13, 1.0]},
        }})

    for i, stem in enumerate(ROWS):
        x = 12.0 + i * 100.0
        n = bx.get(stem + "_n")
        if n:
            n["presentation_rect"] = [x, 192.0, 62.0, 20.0]
        el = bx.get(stem + "_l")
        if el:
            el["presentation_rect"] = [x, 176.0, 40.0, 13.0]
            el["fontsize"] = 8.0

    if "mk_btn" in bx:
        bx["mk_btn"]["presentation_rect"] = [908.0, 192.0, 18.0, 18.0]
    if "mk_lbl" in bx:
        bx["mk_lbl"]["presentation_rect"] = [900.0, 176.0, 34.0, 13.0]
        bx["mk_lbl"]["fontsize"] = 8.0

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
