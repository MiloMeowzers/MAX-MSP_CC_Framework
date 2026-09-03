"""v6_198 -- arm discipline + adopt the user's diag/probe layout.

Process fixes the user has asked for repeatedly:
 1. Arm toggle (obj-29) always loads OFF: parameter_initial_enable 1,
    parameter_initial [0]. No more "already armed" from a dragged-in build.
 2. Full INIT turns arm OFF: obj-134[0] (the full INIT trigger, fired by the
    full_INIT button AND by RE_INIT on load) -> `set 0` to obj-29 (UI) and
    `0` -> s ---prerollArm (stops the ring). No more silence-fill after INIT.
 3. Diag/probe layout matched to the user's own edit of v6_195:
    - dg_*_n number stack at presentation x 1008 (the debug-panel area), y 8..
    - dg_frc_n / dg_cap_n -> flonum (float display; that's why FRC finally
      read 0.114 in their edit).
    - dg_*_l labels at x 1075.
    - mk_btn at [957, 14.5], mk_lbl at [975, 16.5].
    - preroll_led at [831.68, 13].

Handoff (p PrerollCapture) unchanged from v6_197 -- the bare-message bisect,
now testable on a clean preroll.

    python phase3_file15_arm_discipline_layout.py   # -> ../generated/ChopChop_v6_198.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_197.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_198.amxd"

DIAG_Y = {  # id-stem : (presentation y, is_float)
    "dg_ply": (8.0, False), "dg_frc": (33.6, True), "dg_hc": (59.2, False),
    "dg_ful": (84.8, False), "dg_siz": (110.4, False), "dg_cap": (136.0, True),
    "dg_hnd": (161.6, False),
}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    bx = {b.get("box", b)["id"]: b.get("box", b) for b in root["boxes"]}

    # 1. arm toggle always loads OFF
    vo = bx["obj-29"].setdefault("saved_attribute_attributes", {}).setdefault("valueof", {})
    vo["parameter_initial_enable"] = 1
    vo["parameter_initial"] = [0]

    # 2. full INIT -> arm off
    for nid, txt, w in (("ri_arm0", "set 0", 44), ("ri_ps0", "0", 26)):
        assert nid not in bx
    root["boxes"] += [
        {"box": {"id": "ri_arm0", "maxclass": "message", "text": "set 0", "numinlets": 2,
                 "numoutlets": 1, "outlettype": [""], "patching_rect": [700.0, 330.0, 44.0, 20.0]}},
        {"box": {"id": "ri_ps0", "maxclass": "message", "text": "0", "numinlets": 2, "numoutlets": 1,
                 "outlettype": [""], "patching_rect": [750.0, 330.0, 26.0, 20.0]}},
        {"box": {"id": "ri_pss", "maxclass": "newobj", "text": "s ---prerollArm", "numinlets": 1,
                 "numoutlets": 0, "patching_rect": [750.0, 356.0, 110.0, 20.0]}},
    ]
    root["lines"] += [
        Ln("obj-134", 0, "ri_arm0", 0), Ln("ri_arm0", 0, "obj-29", 0),
        Ln("obj-134", 0, "ri_ps0", 0), Ln("ri_ps0", 0, "ri_pss", 0),
    ]

    # 3. reposition diag stack + convert frc/cap to flonum
    for stem, (py, is_float) in DIAG_Y.items():
        n = bx.get(stem + "_n")
        if n:
            n["presentation_rect"] = [1008.0, py, 57.0, 20.0]
            n["patching_rect"] = [2720.0, 260.0 + list(DIAG_Y).index(stem) * 25.0, 70.0, 20.0]
            if is_float:
                n["maxclass"] = "flonum"
                n["numoutlets"] = 2
                n["outlettype"] = ["", "bang"]
        lbl = bx.get(stem + "_l")
        if lbl:
            lbl["presentation_rect"] = [1075.0, py + 4.0, 26.0, 15.0]

    if "mk_btn" in bx:
        bx["mk_btn"]["presentation_rect"] = [957.0, 14.5, 16.0, 16.0]
    if "mk_lbl" in bx:
        bx["mk_lbl"]["presentation_rect"] = [975.0, 16.5, 24.0, 15.0]
    if "preroll_led" in bx:
        bx["preroll_led"]["presentation_rect"] = [831.6781039768066, 13.0, 14.0, 14.0]

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
