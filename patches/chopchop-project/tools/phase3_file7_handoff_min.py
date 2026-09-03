"""v6_190 -- strip p PrerollCapture to the minimum, karma message FIRST.

v6_189 still silent; only ---capturedMs (K_4) visibly changes on Record. The
fraction is still effectively 0 (pc_szf was an empty `f` -> bang emits nothing
-> the `maximum 500` floor never fires -> window $1 = 0 -> silence). And the
housekeeping sends (regrid especially) fire before the karma message and may
re-window karma to 0.

This build:
 - pc_szf -> `f 4000`  (real default; bang always emits >= 4000 -> maximum 500
   -> / 120000. -> ~0.033, never 0).
 - pc_t reordered: KARMA `set ---thisBuffer, window $1, jump 0., play` fires
   FIRST (outlet 4), then prerollLoop 1 / hasContent 1 / capturedMs 120000 /
   regrid.  Nothing can re-window karma after the play.
 - metro keep-alive unchanged.
 - manual probe pk_btn / ---pcFracDiag still present (root).

If this still won't play a stable windowed loop, `set`+`window` on a
never-recorded buffer is too unreliable for the feature and preroll pivots to
a real karma-B record pass (Phase 5 alternate-role handoff, early).

    python phase3_file7_handoff_min.py   # -> ../generated/ChopChop_v6_190.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_189.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_190.amxd"


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
        O("pc_t", "t b b b b b", 20, 50, 90, nin=1, nout=5,
          ot=["bang", "bang", "bang", "bang", "bang"]),

        # --- fraction (always non-zero) ---
        O("pc_szr", "r ---size", 320, 20, 90, nin=0, nout=1),
        O("pc_szf", "f 4000", 320, 46, 50),
        O("pc_szmax", "maximum 500", 320, 72, 80),
        O("pc_szdiv", "/ 120000.", 320, 98, 70),
        O("pc_fdiag", "s ---pcFracDiag", 320, 124, 120, nin=1, nout=0),

        # --- outlet 4 (FIRST): karma set/window/jump/play ---
        O("pc_pre", "t b b", 20, 84, 44, nin=1, nout=2, ot=["bang", "bang"]),
        M("pc_msg", "set ---thisBuffer, window $1, jump 0., play", 20, 112, 290),
        O("pc_kmsg", "s ---karmaMsg", 20, 138, 110, nin=1, nout=0),

        # --- then housekeeping ---
        M("pc_pl1", "1", 20, 170, 26), O("pc_pls", "s ---prerollLoop", 56, 170, 120, nin=1, nout=0),
        M("pc_hc1", "1", 20, 196, 26), O("pc_hcs", "s ---hasContent", 56, 196, 120, nin=1, nout=0),
        M("pc_cap", "120000", 20, 222, 60), O("pc_caps", "s ---capturedMs", 90, 222, 120, nin=1, nout=0),
        M("pc_rg", "bang", 20, 248, 40), O("pc_rgs", "s ---regrid", 64, 248, 90, nin=1, nout=0),

        # --- keep-alive ---
        O("pc_kasz", "r ---size", 500, 40, 90, nin=0, nout=1),
        O("pc_plr", "r ---prerollLoop", 500, 66, 120, nin=0, nout=1),
        O("pc_kam", "metro 4000", 500, 92, 80, nin=2, nout=1, ot=["bang"]),
        M("pc_jm", "jump 0.", 500, 120, 60),
        O("pc_jms", "s ---karmaMsg", 500, 146, 110, nin=1, nout=0),

        # --- prerollLoop clears ---
        O("pc_hcr", "r ---hasContent", 700, 40, 120, nin=0, nout=1),
        O("pc_hcsel", "sel 0", 700, 66, 44, nin=2, nout=2, ot=["bang", ""]),
        O("pc_ronr", "r ---recordOn", 840, 40, 110, nin=0, nout=1),
        M("pc_pl0", "0", 760, 92, 26), O("pc_pls2", "s ---prerollLoop", 760, 118, 120, nin=1, nout=0),
    ]
    L = [
        Ln("pc_trig", 0, "pc_t", 0),
        Ln("pc_szr", 0, "pc_szf", 0),
        Ln("pc_szf", 0, "pc_szmax", 0), Ln("pc_szmax", 0, "pc_szdiv", 0),
        Ln("pc_szdiv", 0, "pc_msg", 1), Ln("pc_szdiv", 0, "pc_fdiag", 0),

        Ln("pc_t", 4, "pc_pre", 0),
        Ln("pc_pre", 1, "pc_szf", 0),          # emit current size -> $1
        Ln("pc_pre", 0, "pc_msg", 0),          # then fire karma message
        Ln("pc_msg", 0, "pc_kmsg", 0),

        Ln("pc_t", 3, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),
        Ln("pc_t", 2, "pc_hc1", 0), Ln("pc_hc1", 0, "pc_hcs", 0),
        Ln("pc_t", 1, "pc_cap", 0), Ln("pc_cap", 0, "pc_caps", 0),
        Ln("pc_t", 0, "pc_rg", 0), Ln("pc_rg", 0, "pc_rgs", 0),

        Ln("pc_kasz", 0, "pc_kam", 1), Ln("pc_plr", 0, "pc_kam", 0),
        Ln("pc_kam", 0, "pc_jm", 0), Ln("pc_jm", 0, "pc_jms", 0),

        Ln("pc_hcr", 0, "pc_hcsel", 0),
        Ln("pc_hcsel", 0, "pc_pl0", 0), Ln("pc_ronr", 0, "pc_pl0", 0),
        Ln("pc_pl0", 0, "pc_pls2", 0),
    ]
    return {"fileversion": 1,
            "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [40.0, 40.0, 1000.0, 300.0], "boxes": B, "lines": L}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    pcap = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "p_prcap")
    pcap["patcher"] = prcap_patcher()
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
