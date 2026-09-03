"""v6_180 -- disconnect the half-built p RollingB from karmaB.

p RollingB fires once per load (onebang armed only by loadbang; r ---bRealign
has no sender) sending karmaB `overdub 0 / record / [delay] / play / record`
with no `stop` first. That leaves karmaB mid-overdub, recording device input
unbidden, at a loop length fixed by that stray pass rather than by the user's
capture. Combined with karmaB mirroring A's messages via gB and (v6_179)
sharing A's speed, karmaB's transport/length state diverges from A's --
observed as spurious records, B at a different length than A, and B snapping
out of reverse after ~1 bar (p RollingB's 2000 ms delay fallback).

Fix: remove the single cord `rollingB[0] -> karmaB[0]`. karmaB then only ever
sees A's real record/play/stop/window via gB = a true mirror of A.

p RollingB itself is left intact (its outlet just goes nowhere) for Phase 3 to
rebuild -- it needs `stop` before `record` and a real `---bRealign` trigger.

    python phase1_file5_disconnect_rollingB.py   # -> ../generated/ChopChop_v6_180.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_179.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_180.amxd"


def main():
    amx = load(BASE)
    pb = find_scope(amx.patcher, "p Playback").patcher

    ids = {b.get("box", b)["id"] for b in pb["boxes"]}
    assert "rollingB" in ids and "karmaB" in ids

    before = len(pb["lines"])
    pb["lines"] = [e for e in pb["lines"]
                   if not (e.get("patchline", e)["source"] == ["rollingB", 0]
                           and e.get("patchline", e)["destination"] == ["karmaB", 0])]
    removed = before - len(pb["lines"])
    assert removed == 1, f"expected to remove 1 cord, removed {removed}"

    amx.save(OUT)

    e = find_scope(load(OUT).patcher, "p Playback")
    assert not any(s == "rollingB" for (s, so, d, di) in e.lines()), "rollingB still has an out cord"
    kb_msgs = sorted(s for (s, so, d, di) in e.lines() if d == "karmaB" and di == 0)
    print("karmaB message-inlet feeders now:", kb_msgs)

    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
