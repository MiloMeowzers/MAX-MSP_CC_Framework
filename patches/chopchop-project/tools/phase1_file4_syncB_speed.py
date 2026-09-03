"""v6_179 -- sample-lock karmaB to karma A by sharing the speed signal.

karmaB's speed inlet was fed by its own `bspeed sig~ 1`, independent of karma
A's speed chain (sig~ 1 -> *~ -> *~ <-MessagesToKarma -> *~ <-transport ->
karma A[2], also feeding karmaKeys[2]). Two independent unity signals still let
the two playheads drift apart -- user hears B constantly out of step with A.

Fix: feed karmaB[2] from `obj-7` (the end of karma A's speed chain, the same
node karmaKeys already taps), and drop the now-orphaned `bspeed`. All three
karma instances then share one speed signal incl. every transport/glitch
modulation, so B tracks A exactly.

(This is deliberately reversed again in Phase 3-5 when karmaB becomes the
independent transport-locked rolling-capture voice.)

    python phase1_file4_syncB_speed.py   # -> ../generated/ChopChop_v6_179.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_178.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_179.amxd"


def main():
    amx = load(BASE)
    pb = find_scope(amx.patcher, "p Playback").patcher

    ids = {b.get("box", b)["id"] for b in pb["boxes"]}
    assert "bspeed" in ids and "obj-7" in ids and "karmaB" in ids

    # drop bspeed box + its only line, reroute karmaB[2] from obj-7
    before_l = len(pb["lines"])
    pb["lines"] = [e for e in pb["lines"]
                   if (e.get("patchline", e)["source"] != ["bspeed", 0]
                       or e.get("patchline", e)["destination"] != ["karmaB", 2])]
    assert before_l - len(pb["lines"]) == 1

    before_b = len(pb["boxes"])
    pb["boxes"] = [b for b in pb["boxes"] if b.get("box", b)["id"] != "bspeed"]
    assert before_b - len(pb["boxes"]) == 1

    pb["lines"].append({"patchline": {"source": ["obj-7", 0], "destination": ["karmaB", 2]}})

    amx.save(OUT)

    e = find_scope(load(OUT).patcher, "p Playback")
    assert "bspeed" not in {b.get("box", b)["id"] for b in e.patcher["boxes"]}
    feeders = sorted(s for (s, so, d, di) in e.lines() if d == "karmaB" and di == 2)
    assert feeders == ["obj-7"], feeders
    # obj-7 now feeds A, Keys, B
    o7 = sorted((d, di) for (s, so, d, di) in e.lines() if s == "obj-7")
    print("obj-7 speed fan-out:", o7)

    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
