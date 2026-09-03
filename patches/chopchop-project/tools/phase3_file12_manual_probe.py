"""v6_195 -- diagnostics only: presentation MANUAL button + SIZ/CAP on the strip.

v6_194: FRC(=---windowVal) 1 when armed, 0 after Record; PLY 0; HC 1. Even the
`f 0.05` fallback window doesn't make karma play from the handoff -- but the
manual `set/window/jump/play` message played in v6_188/190. So one of the
handoff's other sends (---hasContent 1 / ---capturedMs / ---regrid / the bare
`set`) is blocking the karma message.

No logic change. Adds, in presentation next to the diag strip:
 - `mk_btn` button -> `set ---thisBuffer, window 0.05, jump 0., play` ->
   s ---karmaMsg   (NOTHING else -- the isolation test)
 - SIZ (r ---size) and CAP (r ---capturedMs) number boxes on the strip

Test: after a failed handoff, click MANUAL. If karma plays -> a handoff send
is the blocker (I'll bisect). If not -> `set`+`window` itself regressed.

    python phase3_file12_manual_probe.py   # -> ../generated/ChopChop_v6_195.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_194.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_195.amxd"
ORANGE = [1.0, 0.709803921568627, 0.196078431372549, 1.0]


def num_diag(i, ch, prx, pry, lbl):
    return [
        {"box": {"id": i + "_r", "maxclass": "newobj", "text": "r " + ch, "numinlets": 0,
                 "numoutlets": 1, "outlettype": [""], "patching_rect": [2600.0, pry, 110.0, 20.0]}},
        {"box": {"id": i + "_n", "maxclass": "number", "numinlets": 1, "numoutlets": 2,
                 "outlettype": ["", "bang"], "patching_rect": [2720.0, pry, 70.0, 22.0],
                 "presentation": 1, "presentation_rect": [prx, pry - 200.0, 34.0, 13.0]}},
        {"box": {"id": i + "_l", "maxclass": "comment", "text": lbl, "numinlets": 1, "numoutlets": 0,
                 "patching_rect": [2800.0, pry, 40.0, 18.0], "presentation": 1,
                 "presentation_rect": [prx + 35.0, pry - 200.0, 24.0, 12.0],
                 "textcolor": ORANGE, "fontsize": 7.0}},
    ]


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    ids = {b.get("box", b)["id"] for b in root["boxes"]}
    assert "mk_btn" not in ids

    root["boxes"] += num_diag("dg_siz", "---size", 888.0, 360.0, "SIZ")
    root["boxes"] += num_diag("dg_cap", "---capturedMs", 888.0, 385.0, "CAP")
    root["lines"] += [Ln("dg_siz_r", 0, "dg_siz_n", 0), Ln("dg_cap_r", 0, "dg_cap_n", 0)]

    root["boxes"] += [
        {"box": {"id": "mk_btn", "maxclass": "button", "numinlets": 1, "numoutlets": 1,
                 "outlettype": ["bang"], "patching_rect": [2600.0, 410.0, 24.0, 24.0],
                 "presentation": 1, "presentation_rect": [890.0, 220.0, 16.0, 16.0]}},
        {"box": {"id": "mk_lbl", "maxclass": "comment", "text": "MAN", "numinlets": 1, "numoutlets": 0,
                 "patching_rect": [2800.0, 410.0, 40.0, 18.0], "presentation": 1,
                 "presentation_rect": [908.0, 222.0, 22.0, 12.0], "textcolor": ORANGE, "fontsize": 7.0}},
        {"box": {"id": "mk_msg", "maxclass": "message",
                 "text": "set ---thisBuffer, window 0.05, jump 0., play",
                 "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                 "patching_rect": [2635.0, 410.0, 280.0, 20.0]}},
        {"box": {"id": "mk_s", "maxclass": "newobj", "text": "s ---karmaMsg", "numinlets": 1,
                 "numoutlets": 0, "patching_rect": [2635.0, 436.0, 110.0, 20.0]}},
    ]
    root["lines"] += [Ln("mk_btn", 0, "mk_msg", 0), Ln("mk_msg", 0, "mk_s", 0)]

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
