"""v6_188 -- handoff still silent: reorder, use proven `jump`, add a manual probe.

v6_187: Record with preroll full -> ---regrid fires (overlays vanish) but karma
never plays. p PrerollCapture IS running; karma isn't taking the message.

Changes:
 - pc_msg -> `set ---thisBuffer, window $1, jump 0., play`  (jump, not the
   untested `position 0.`; matches the prototype variant that looped cleanly).
 - pc_t reordered so the karma set/window/play fires LAST -- after
   prerollLoop / capturedMs / hasContent / regrid -- so the device's own
   regrid-driven `window` re-send can't land after `play`.
 - NEW root probe: button `pk_btn` -> `set ---thisBuffer, window 0.033, jump 0.,
   play` -> s ---karmaMsg, labelled "MANUAL KARMA TEST", near x2600 y430.
   Click it after a failed handoff: if karma plays THEN, the bug is in
   p PrerollCapture's trigger/construction; if it's still silent, the
   post-handoff device state (hasContent=1 + regrid) is blocking karma.
 - pc_fracf value mirrored to a root number box via s/r ---pcFracDiag.

    python phase3_file5_handoff_debug.py   # -> ../generated/ChopChop_v6_188.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_187.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_188.amxd"


def prcap_patcher():
    def O(i, t, x, y, w=120, nin=2, nout=1, ot=None):
        return {"box": {"id": i, "maxclass": "newobj", "text": t, "numinlets": nin,
                        "numoutlets": nout, "outlettype": ot if ot is not None else [""],
                        "patching_rect": [float(x), float(y), float(w), 20.0]}}

    def M(i, t, x, y, w=120):
        return {"box": {"id": i, "maxclass": "message", "text": t, "numinlets": 2, "numoutlets": 1,
                        "outlettype": [""], "patching_rect": [float(x), float(y), float(w), 20.0]}}

    B = [
        O("pc_trig", "r ---prerollCapture", 20, 20, 140, nin=0, nout=1),
        O("pc_sizer", "r ---size", 320, 20, 90, nin=0, nout=1),
        O("pc_frac", "/ 120000.", 320, 46, 70),
        O("pc_fracf", "f 0.0667", 320, 72, 60),
        O("pc_fdiag", "s ---pcFracDiag", 320, 98, 120, nin=1, nout=0),

        O("pc_t", "t b b b b b", 20, 56, 90, nin=1, nout=5,
          ot=["bang", "bang", "bang", "bang", "bang"]),
        M("pc_pl1", "1", 20, 84, 26), O("pc_pls", "s ---prerollLoop", 56, 84, 120, nin=1, nout=0),
        M("pc_cap", "120000", 20, 110, 60), O("pc_caps", "s ---capturedMs", 90, 110, 120, nin=1, nout=0),
        M("pc_hc1", "1", 20, 136, 26), O("pc_hcs", "s ---hasContent", 56, 136, 120, nin=1, nout=0),
        M("pc_rg", "bang", 20, 162, 40), O("pc_rgs", "s ---regrid", 64, 162, 90, nin=1, nout=0),
        O("pc_lastt", "t b b", 20, 190, 44, nin=1, nout=2, ot=["bang", "bang"]),
        M("pc_msg", "set ---thisBuffer, window $1, jump 0., play", 20, 220, 290),
        O("pc_kmsg", "s ---karmaMsg", 20, 246, 110, nin=1, nout=0),

        O("pc_se", "r ---sliceEdge", 460, 60, 110, nin=0, nout=1),
        O("pc_cnt", "counter 0 15", 460, 86, 90, nin=5, nout=4, ot=["int", "int", "int", "int"]),
        O("pc_kag", "gate 1", 460, 114, 54, nin=2, nout=1),
        O("pc_plr", "r ---prerollLoop", 600, 60, 120, nin=0, nout=1),
        M("pc_jm", "jump 0.", 460, 142, 60),
        O("pc_jms", "s ---karmaMsg", 460, 170, 110, nin=1, nout=0),

        O("pc_hcr", "r ---hasContent", 680, 100, 120, nin=0, nout=1),
        O("pc_hcsel", "sel 0", 680, 126, 44, nin=2, nout=2, ot=["bang", ""]),
        O("pc_ronr", "r ---recordOn", 820, 100, 110, nin=0, nout=1),
        M("pc_pl0", "0", 740, 152, 26), O("pc_pls2", "s ---prerollLoop", 740, 178, 120, nin=1, nout=0),
    ]
    L = [
        Ln("pc_trig", 0, "pc_t", 0),
        Ln("pc_sizer", 0, "pc_frac", 0), Ln("pc_frac", 0, "pc_fracf", 0),
        Ln("pc_fracf", 0, "pc_fdiag", 0),
        Ln("pc_fracf", 0, "pc_msg", 1),
        # order: prerollLoop 1 / capturedMs 120000 / hasContent 1 / regrid / THEN karma
        Ln("pc_t", 4, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),
        Ln("pc_t", 3, "pc_cap", 0), Ln("pc_cap", 0, "pc_caps", 0),
        Ln("pc_t", 2, "pc_hc1", 0), Ln("pc_hc1", 0, "pc_hcs", 0),
        Ln("pc_t", 1, "pc_rg", 0), Ln("pc_rg", 0, "pc_rgs", 0),
        Ln("pc_t", 0, "pc_lastt", 0),
        Ln("pc_lastt", 1, "pc_fracf", 0),        # refresh $1
        Ln("pc_lastt", 0, "pc_msg", 0),          # then fire the karma message (last of all)
        Ln("pc_msg", 0, "pc_kmsg", 0),

        Ln("pc_se", 0, "pc_cnt", 0),
        Ln("pc_cnt", 2, "pc_kag", 1),
        Ln("pc_plr", 0, "pc_kag", 0),
        Ln("pc_kag", 0, "pc_jm", 0), Ln("pc_jm", 0, "pc_jms", 0),

        Ln("pc_hcr", 0, "pc_hcsel", 0),
        Ln("pc_hcsel", 0, "pc_pl0", 0), Ln("pc_ronr", 0, "pc_pl0", 0),
        Ln("pc_pl0", 0, "pc_pls2", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 980.0, 320.0], "boxes": B, "lines": L}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    pcap = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_prcap")
    pcap["patcher"] = prcap_patcher()

    ids = {b.get("box", b)["id"] for b in root["boxes"]}
    assert "pk_btn" not in ids
    root["boxes"] += [
        {"box": {"id": "pk_btn", "maxclass": "button", "numinlets": 1, "numoutlets": 1,
                 "outlettype": ["bang"], "patching_rect": [2600.0, 430.0, 26.0, 26.0]}},
        {"box": {"id": "pk_msg", "maxclass": "message",
                 "text": "set ---thisBuffer, window 0.033, jump 0., play",
                 "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                 "patching_rect": [2635.0, 432.0, 290.0, 20.0]}},
        {"box": {"id": "pk_s", "maxclass": "newobj", "text": "s ---karmaMsg", "numinlets": 1,
                 "numoutlets": 0, "patching_rect": [2635.0, 458.0, 110.0, 20.0]}},
        {"box": {"id": "pk_lbl", "maxclass": "comment", "text": "MANUAL KARMA TEST (click after a failed handoff)",
                 "numinlets": 1, "numoutlets": 0, "patching_rect": [2600.0, 408.0, 360.0, 18.0]}},
        {"box": {"id": "pk_fdr", "maxclass": "newobj", "text": "r ---pcFracDiag", "numinlets": 0,
                 "numoutlets": 1, "outlettype": [""], "patching_rect": [2600.0, 484.0, 110.0, 20.0]}},
        {"box": {"id": "pk_fdn", "maxclass": "number", "numinlets": 1, "numoutlets": 2,
                 "outlettype": ["", "bang"], "patching_rect": [2720.0, 484.0, 90.0, 22.0]}},
    ]
    root["lines"] += [
        Ln("pk_btn", 0, "pk_msg", 0), Ln("pk_msg", 0, "pk_s", 0),
        Ln("pk_fdr", 0, "pk_fdn", 0),
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
