"""v6_205 -- Phase 5 file 4: groove~ render source + exact 8x speed + diags.

Base v6_204.  Logic-only; NO presentation / position / openrect change.

v6_204 test (user diagnostic): the handover is FINE now -- karma A plays, the
chase overlay tracks, PLY=1, SPD/FRC track.  But the committed loop is the
**whole 120000 ms buffer, empty** (slices "super slow", audio dies instantly).
So the render pass itself is broken in two ways:

  1. It recorded SILENCE.  The render source was `play~ ---rollBuf` (position-
     driven) piped `send~ ---renderL/R` -> `receive~` -> `selector~` -> karma.
     The user's bench test that confirmed 8x render used `groove~` (rate-driven)
     straight into karma.  -> switch to that exact pattern.
  2. The loop closed at the buffer end (frames-1) instead of `sizeMs`.  karma's
     record head advances at the SPEED-INLET rate; v6_204 fed karma
     `obj-7 + 7` (a `+~` boost on top of an unknown base), which can exceed 8x
     and race the buffer end before `play` lands.  -> feed karma EXACTLY
     `sig~ 8.` during the render via a `selector~`, and `deferlow` the `play`
     so karma processes `record` first.  renderMs floored at 60.

Changes (p Playback + p FastRender + p PrerollCapture + diag repoint):

p Playback
  speed:  remove fr_add(+~)/fr_boost/fr_bsel/fr_b7/fr_b0.  fr_spd (selector~ 2):
     [1] = obj-7, [2] = fr_s8 (sig~ 8.), [0] = fr_ract (+1 on r ---renderActive).
     out -> obj-20[2].  During render: exactly 8x.  Otherwise: obj-7.
  render source:  remove fr_rvL/fr_rvR (receive~ ---renderL/R).  New
     gv2 (groove~ ---rollBuf 2): rate from fr_g2r (selector~ 2): [1] = fr_z
     (sig~ 0.), [2] = fr_s8, [0] = fr_ract -> gv2[0].  Region + play come from
     r ---gv2Msg -> gv2[0].  gv2[0]/gv2[1] -> fr_recL[2]/fr_recR[2] (the karma
     record-source selector~, input 2).

p FastRender  (on r ---commitGo -> unpack f f f = start, end, renderMs)
  fr_fmt sprintf "start %g %g" (start, end) -> s ---gv2Msg  (groove~ region+play)
  sequence:  s ---renderActive 1  (speed 8, rec src -> gv2, gv2 rate 8)
             report 20 / snramp 16 / ramp 16 -> s ---karmaMsg   (reinit BEFORE record)
             s ---karmaMsg stop
             s ---gv2Msg "loop 0" then the "start lo hi" list  (gv2 plays the slab 8x)
             s ---karmaMsg record
             delay <renderMs> -> deferlow -> s ---karmaMsg play   (closes at sizeMs)
                                s ---renderActive 0 (speed -> obj-7, src -> live)
                                s ---regrid ; s ---hasContent 1
                                delay 25 -> s ---prerollLoop 0   (fade the 1x gv bridge)
  s ---frRenderMs = renderMs   (for the diag field)

p PrerollCapture
  pc_spanx renderMs floored:  expr ($f2-$f1<480.)?60.:(($f2-$f1)/8.)

diag repoint (logic only, no layout change):
  dg_spd_r  r ---rollFold   -> r ---karmaRep4   (karma loop END ms: ~sizeMs = OK,
                                                 ~120000 = the render still failed)
  dg_frc_r  r ---rollEndMs  -> r ---frRenderMs  (the renderMs FastRender used)

    python phase3_file22_groove_render.py   # -> ../generated/ChopChop_v6_205.amxd
"""
from pathlib import Path
import copy

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_204.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_205.amxd"


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
    fr = find(root, lambda x: x.get("text") == "p FastRender")["patcher"]
    pc = find(root, lambda x: x.get("text") == "p PrerollCapture")["patcher"]
    SIG = ["signal"]

    # ===================================================== p Playback: speed + gv2
    drop(pb, lambda pl: pl["source"] == ["obj-7", 0] and pl["destination"] == ["fr_add", 0])
    drop(pb, lambda pl: pl["source"] == ["fr_add", 0] and pl["destination"] == ["obj-20", 2])
    drop(pb, lambda pl: pl["source"][0] in ("fr_boost", "fr_bsel", "fr_b7", "fr_b0")
         or pl["destination"][0] in ("fr_add", "fr_boost", "fr_bsel", "fr_b7", "fr_b0"))
    for bid in ("fr_add", "fr_boost", "fr_bsel", "fr_b7", "fr_b0", "fr_rvL", "fr_rvR"):
        pb["boxes"] = [b for b in pb["boxes"] if b.get("box", b)["id"] != bid]
    drop(pb, lambda pl: pl["source"][0] in ("fr_rvL", "fr_rvR")
         or pl["destination"][0] in ("fr_rvL", "fr_rvR"))

    pb["boxes"] += [
        O("fr_s8", "sig~ 8.", 60.0, 12.0, 50.0, nin=1, ot=SIG),
        O("fr_z", "sig~ 0.", 120.0, 12.0, 50.0, nin=1, ot=SIG),
        O("fr_spd", "selector~ 2", 40.0, 44.0, 90.0, nin=3, nout=1, ot=SIG),
        O("fr_g2r", "selector~ 2", 200.0, 44.0, 90.0, nin=3, nout=1, ot=SIG),
        O("gv2", "groove~ ---rollBuf 2", 200.0, 100.0, 150.0, nin=3, nout=3,
          ot=["signal", "signal", "signal"]),
        O("fr_g2m", "r ---gv2Msg", 200.0, 72.0, 100.0, nin=0, ot=[""]),
        O("fr_g2lo", "r ---gv2Lo", 320.0, 72.0, 90.0, nin=0, ot=[""]),
        O("fr_g2hi", "r ---gv2Hi", 420.0, 72.0, 90.0, nin=0, ot=[""]),
    ]
    pb["lines"] += [
        # exact 8x speed selector
        Ln("obj-7", 0, "fr_spd", 1),
        Ln("fr_s8", 0, "fr_spd", 2),
        Ln("fr_ract", 0, "fr_spd", 0),
        Ln("fr_spd", 0, "obj-20", 2),
        # gv2 rate selector (0 idle, 8 during render)
        Ln("fr_z", 0, "fr_g2r", 1),
        Ln("fr_s8", 0, "fr_g2r", 2),
        Ln("fr_ract", 0, "fr_g2r", 0),
        Ln("fr_g2r", 0, "gv2", 0),
        # gv2 messages (set / loop 1 / position float) + loop points
        Ln("fr_g2m", 0, "gv2", 0),
        Ln("fr_g2lo", 0, "gv2", 1),
        Ln("fr_g2hi", 0, "gv2", 2),
        # gv2 audio -> karma record-source selector, input 2
        Ln("gv2", 0, "fr_recL", 2),
        Ln("gv2", 1, "fr_recR", 2),
    ]

    # ===================================================== p FastRender: rework
    fr["boxes"] = [b for b in fr["boxes"] if b.get("box", b)["id"] in
                   ("fr_go", "fr_unpk", "fr_ra1", "fr_ras", "fr_kstop",
                    "fr_krec", "fr_km", "fr_dl", "fr_cl", "fr_ra0", "fr_ras2",
                    "fr_kplay", "fr_rgb", "fr_rg", "fr_hc1", "fr_hcs", "fr_dl2",
                    "fr_pl0", "fr_pls", "fr_rainit", "fr_rais", "fr_reit",
                    "fr_rep", "fr_snr", "fr_rmp")]
    fr["lines"] = []
    fr["boxes"] += [
        # groove~ region + play, matching the verified probe: loop points via
        # ---gv2Lo/Hi (-> gv2 inlets 1/2), then "set ---rollBuf" + "loop 1", then a
        # float position (= lo) into gv2 inlet 0 to begin playback (rate is 8 by now).
        O("fr_lof", "t b f", 300.0, 56.0, 50.0, nin=1, nout=2, ot=["bang", "float"]),
        O("fr_los", "s ---gv2Lo", 380.0, 88.0, 90.0, nout=0),
        O("fr_his", "s ---gv2Hi", 150.0, 56.0, 90.0, nout=0),
        O("fr_posf", "f", 300.0, 200.0, 40.0, nin=2, ot=[""]),
        O("fr_seq", "t b b b b", 300.0, 96.0, 90.0, nin=1, nout=4, ot=["bang"] * 4),
        M("fr_g2set", "set ---rollBuf", 400.0, 128.0, 110.0),
        M("fr_g2l1", "loop 1", 400.0, 156.0, 50.0),
        O("fr_g2s", "s ---gv2Msg", 300.0, 240.0, 90.0, nout=0),
        O("fr_ks2", "t b b", 200.0, 230.0, 60.0, nin=1, nout=2, ot=["bang", "bang"]),
        O("fr_defer", "deferlow", 430.0, 300.0, 70.0, nin=1, ot=["bang"]),
        O("fr_rms_s", "s ---frRenderMs", 150.0, 92.0, 110.0, nout=0),
    ]
    fr["lines"] += [
        Ln("fr_go", 0, "fr_unpk", 0),
        Ln("fr_unpk", 2, "fr_dl", 1),
        Ln("fr_unpk", 2, "fr_rms_s", 0),
        Ln("fr_unpk", 1, "fr_his", 0),          # end -> ---gv2Hi (loopmax)
        Ln("fr_unpk", 0, "fr_lof", 0),          # start -> t b f
        # lof: f outlet first -> ---gv2Lo (loopmin) & store the position; b -> fr_seq
        Ln("fr_lof", 1, "fr_los", 0),
        Ln("fr_lof", 1, "fr_posf", 1),
        Ln("fr_lof", 0, "fr_seq", 0),
        # fr_seq fires o3..o0:
        Ln("fr_seq", 3, "fr_g2set", 0), Ln("fr_g2set", 0, "fr_g2s", 0),   # set ---rollBuf
        Ln("fr_seq", 2, "fr_g2l1", 0), Ln("fr_g2l1", 0, "fr_g2s", 0),     # loop 1
        Ln("fr_seq", 1, "fr_ra1", 0), Ln("fr_ra1", 0, "fr_ras", 0),       # renderActive 1 (rate 8)
        # o0: gv2 position float (plays), THEN the karma sequence
        Ln("fr_seq", 0, "fr_ks2", 0),
        Ln("fr_seq", 0, "fr_posf", 0), Ln("fr_posf", 0, "fr_g2s", 0),
        # karma: reinit -> stop -> record + close timer
        Ln("fr_ks2", 1, "fr_reit", 0),
        Ln("fr_reit", 2, "fr_rep", 0), Ln("fr_reit", 1, "fr_snr", 0), Ln("fr_reit", 0, "fr_rmp", 0),
        Ln("fr_rep", 0, "fr_km", 0), Ln("fr_snr", 0, "fr_km", 0), Ln("fr_rmp", 0, "fr_km", 0),
        Ln("fr_ks2", 1, "fr_kstop", 0), Ln("fr_kstop", 0, "fr_km", 0),
        Ln("fr_ks2", 0, "fr_krec", 0), Ln("fr_krec", 0, "fr_km", 0),
        Ln("fr_ks2", 0, "fr_dl", 0),
        Ln("fr_dl", 0, "fr_cl", 0),
        Ln("fr_cl", 4, "fr_ra0", 0), Ln("fr_ra0", 0, "fr_ras2", 0),
        Ln("fr_cl", 3, "fr_defer", 0), Ln("fr_defer", 0, "fr_kplay", 0), Ln("fr_kplay", 0, "fr_km", 0),
        Ln("fr_cl", 2, "fr_rgb", 0), Ln("fr_rgb", 0, "fr_rg", 0),
        Ln("fr_cl", 1, "fr_hc1", 0), Ln("fr_hc1", 0, "fr_hcs", 0),
        Ln("fr_cl", 0, "fr_dl2", 0),
        Ln("fr_dl2", 0, "fr_pl0", 0), Ln("fr_pl0", 0, "fr_pls", 0),
        Ln("fr_rainit", 0, "fr_rais", 0),
    ]

    # ===================================================== p PrerollCapture: renderMs floor
    for b in pc["boxes"]:
        bx = b.get("box", b)
        if bx["id"] == "pc_spanx":
            bx["text"] = "expr ($f2-$f1<480.)?60.:(($f2-$f1)/8.)"

    # ===================================================== diag repoint (logic only)
    rb = {b.get("box", b)["id"]: b.get("box", b) for b in root["boxes"]}
    rb["dg_spd_r"]["text"] = "r ---karmaRep4"
    rb["dg_frc_r"]["text"] = "r ---frRenderMs"

    # -------------------------------------------------------------- save + check
    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_204 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
