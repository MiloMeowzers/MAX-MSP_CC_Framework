"""validate -- per-scope structural checks + message-cycle sweep for a ChopChop .amxd.

Runs, per subpatcher scope (IDs are scope-local, so every check is scope-qualified):

  * every patchline source/destination id exists in that scope
  * source outlet index < numoutlets, destination inlet index < numinlets
  * no duplicate patchcords (identical src/outlet/dst/inlet)
  * no duplicate box ids
  * no duplicate varnames
  * elementary message cycles, patchline-only (no send/receive, no subpatcher
    crossing). The v6_174 baseline total is 27 -- anything above that is new and
    must be accounted for (delivery checklist, doc 19 Part D).

Usage:
  python validate.py FILE                      # absolute report
  python validate.py FILE --baseline BASE.amxd # diff against a known-clean file;
                                               # exit 1 if the edit adds problems
                                               # or changes the cycle total
"""
from __future__ import annotations

import sys

from ccamxd import load, iter_scopes


# ---------------------------------------------------- Johnson elementary cycles

def _elementary_cycles(nodes, succ):
    """Count elementary cycles of a directed graph (Johnson 1975).

    nodes: iterable of node keys.  succ: dict node -> set(nodes).
    Returns the number of distinct elementary cycles (self-loops included).
    """
    nodes = list(nodes)
    index = {n: i for i, n in enumerate(nodes)}
    count = 0

    # operate on the subgraph induced by nodes with index >= s, using Tarjan SCCs
    def sccs_from(start_i):
        sub = nodes[start_i:]
        subset = set(sub)
        idx = {}
        low = {}
        onstk = {}
        stk = []
        out = []
        counter = [0]

        def strong(v):
            idx[v] = low[v] = counter[0]
            counter[0] += 1
            stk.append(v)
            onstk[v] = True
            for w in succ.get(v, ()):
                if w not in subset:
                    continue
                if w not in idx:
                    strong(w)
                    low[v] = min(low[v], low[w])
                elif onstk.get(w):
                    low[v] = min(low[v], idx[w])
            if low[v] == idx[v]:
                comp = []
                while True:
                    w = stk.pop()
                    onstk[w] = False
                    comp.append(w)
                    if w == v:
                        break
                out.append(comp)

        for v in sub:
            if v not in idx:
                strong(v)
        return out

    s_i = 0
    while s_i < len(nodes):
        comps = sccs_from(s_i)
        # pick the SCC (size>1, or self-loop) containing the least-indexed vertex
        cand = [c for c in comps if len(c) > 1 or (len(c) == 1 and c[0] in succ.get(c[0], ()))]
        if not cand:
            s_i += 1
            continue
        comp = min(cand, key=lambda c: min(index[x] for x in c))
        comp_set = set(comp)
        s = min(comp, key=lambda x: index[x])

        blocked = {v: False for v in comp}
        B = {v: set() for v in comp}
        path = []

        def unblock(v):
            blocked[v] = False
            for w in list(B[v]):
                B[v].discard(w)
                if blocked.get(w):
                    unblock(w)

        def circuit(v):
            nonlocal count
            found = False
            path.append(v)
            blocked[v] = True
            for w in succ.get(v, ()):
                if w not in comp_set:
                    continue
                if w == s:
                    count += 1
                    found = True
                elif not blocked.get(w):
                    if circuit(w):
                        found = True
            if found:
                unblock(v)
            else:
                for w in succ.get(v, ()):
                    if w in comp_set:
                        B[w].add(v)
            path.pop()
            return found

        circuit(s)
        s_i = index[s] + 1

    return count


# ----------------------------------------------------------------- scope checks

def check_scope(sc):
    problems = []
    ids = list(sc.boxes.keys())
    seen = set()
    for i in ids:
        if i in seen:
            problems.append(("dup-id", i))
        seen.add(i)

    vn = {}
    for bid, b in sc.iter_boxes():
        v = b.get("varname")
        if v:
            vn.setdefault(v, []).append(bid)
    for v, where in vn.items():
        if len(where) > 1:
            problems.append(("dup-varname", f"{v} @ {where}"))

    cords = set()
    for s, so, d, di in sc.lines():
        if s not in sc.boxes:
            problems.append(("dangling-src", f"{s}[{so}] -> {sc.label(d)}[{di}]"))
        else:
            no = sc.numoutlets(s)
            if no is not None and so >= no:
                problems.append(("outlet-oob", f"{sc.label(s)} outlet {so} >= numoutlets {no}"))
        if d not in sc.boxes:
            problems.append(("dangling-dst", f"{sc.label(s)}[{so}] -> {d}[{di}]"))
        else:
            ni = sc.numinlets(d)
            if ni is not None and di >= ni:
                problems.append(("inlet-oob", f"{sc.label(d)} inlet {di} >= numinlets {ni}"))
        key = (s, so, d, di)
        if key in cords:
            problems.append(("dup-cord", f"{sc.label(s)}[{so}] -> {sc.label(d)}[{di}]"))
        cords.add(key)

    # patchline-only cycle count (box -> box adjacency)
    succ = {}
    for s, so, d, di in sc.lines():
        if s in sc.boxes and d in sc.boxes:
            succ.setdefault(s, set()).add(d)
    cyc = _elementary_cycles(sc.boxes.keys(), succ)
    return problems, cyc


def sweep(amx):
    total_cyc = 0
    per = {}
    probs = {}
    for sc in iter_scopes(amx.patcher):
        p, c = check_scope(sc)
        per[sc.path] = c
        total_cyc += c
        if p:
            probs[sc.path] = p
    return per, total_cyc, probs


def _cli(argv):
    if not argv:
        print(__doc__)
        return 2
    amx = load(argv[0])
    per, total, probs = sweep(amx)

    print(f"=== {argv[0]}")
    print(f"scopes: {len(per)}   message-cycle total (patchline-only): {total}")
    for path, c in per.items():
        if c:
            print(f"  cycles {c:>3}  {path}")
    if probs:
        print("STRUCTURAL PROBLEMS:")
        for path, plist in probs.items():
            for kind, detail in plist:
                print(f"  [{kind}] {path}  {detail}")
    else:
        print("structural: clean (0 problems)")

    if "--baseline" in argv:
        base = load(argv[argv.index("--baseline") + 1])
        bper, btot, bprobs = sweep(base)
        print(f"\n=== baseline total cycles {btot}, problems {sum(len(v) for v in bprobs.values())}")
        new_probs = sum(len(v) for v in probs.values()) - sum(len(v) for v in bprobs.values())
        ok = True
        if total != btot:
            print(f"CYCLE TOTAL CHANGED: {btot} -> {total}")
            for path in per:
                if per.get(path, 0) != bper.get(path, 0):
                    print(f"  {path}: {bper.get(path,0)} -> {per.get(path,0)}")
            ok = False
        if new_probs > 0:
            print(f"NEW STRUCTURAL PROBLEMS: +{new_probs}")
            ok = False
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
