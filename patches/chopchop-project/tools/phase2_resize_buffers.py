"""v6_183 -- Phase 2: resize ---bufB / ---bufFreeze from 20,000 to 120,000 ms.

Both are declared in p Playback/p BufferSwitching, hardcoded at 20000 ms, with
no reduction guard (only ---thisBuffer has one, via loadmess 120000 ->
s ---bufferMs -> the p TempoTranslate divisor walk). So any karmaB / karmaKeys
capture over 20 s wraps and corrupts. Match ---thisBuffer at 120000.

Just edits the size arg in the two existing `buffer~` declarations -- no boxes
added or reordered, so the "buffer decls are order-sensitive" rule is not in
play. New allocation ~42 MB/buffer stereo @ 44.1k; ~127 MB total across the
four. Applied on the next device load.

    python phase2_resize_buffers.py   # -> ../generated/ChopChop_v6_183.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_182.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_183.amxd"

CHANGES = {
    "bufB": ("buffer~ ---bufB 20000 2", "buffer~ ---bufB 120000 2"),
    "bufFreeze": ("buffer~ ---bufFreeze 20000 2", "buffer~ ---bufFreeze 120000 2"),
}


def main():
    amx = load(BASE)
    bs = find_scope(amx.patcher, "p BufferSwitching").patcher

    idx = {}
    for entry in bs["boxes"]:
        b = entry.get("box", entry)
        idx[b["id"]] = b

    for bid, (old, new) in CHANGES.items():
        assert bid in idx, f"missing box {bid}"
        assert idx[bid].get("text") == old, f"{bid} text is {idx[bid].get('text')!r}, expected {old!r}"
        idx[bid]["text"] = new

    amx.save(OUT)

    e = find_scope(load(OUT).patcher, "p BufferSwitching")
    for bid, (_, new) in CHANGES.items():
        got = e.boxes[bid].get("text")
        print(f"{bid}: {got!r}  {'OK' if got == new else 'MISMATCH'}")
    # declaration order unchanged
    order = [entry.get("box", entry)["id"] for entry in e.patcher["boxes"]]
    print("box order:", order)

    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
