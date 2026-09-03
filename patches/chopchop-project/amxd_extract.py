"""Extract the embedded JSON patcher from a .amxd (read-only inspection)."""
import json, sys

def extract(path):
    data = open(path, 'rb').read()
    m = data.find(b'mx@c')
    if m < 0:
        # some .amxd are plain JSON
        return json.loads(data.decode('utf-8', 'replace'))
    i = data.find(b'{', m)
    depth = 0; instr = False; esc = False
    start = i
    while i < len(data):
        c = data[i:i+1]
        if esc:
            esc = False
        elif c == b'\\':
            esc = True
        elif c == b'"':
            instr = not instr
        elif not instr:
            if c == b'{':
                depth += 1
            elif c == b'}':
                depth -= 1
                if depth == 0:
                    blob = data[start:i+1]
                    return json.loads(blob.decode('utf-8', 'replace'))
        i += 1
    raise RuntimeError('no balanced brace')

def walk(patcher, path='/'):
    """Yield (scopepath, box) for every box, recursing subpatchers."""
    boxes = patcher.get('boxes', [])
    for b in boxes:
        bb = b.get('box', b)
        yield path, bb
        sp = bb.get('patcher')
        if sp:
            name = bb.get('text','') or bb.get('varname','') or '?'
            yield from walk(sp, path + name.replace('p ','').strip()[:24] + '/')

if __name__ == '__main__':
    p = extract(sys.argv[1])
    pat = p.get('patcher', p)
    allb = list(walk(pat))
    print(f'total boxes (recursive): {len(allb)}')
    q = sys.argv[2] if len(sys.argv) > 2 else None
    if q:
        ql = q.lower()
        for sp, b in allb:
            t = (b.get('text') or b.get('varname') or b.get('maxclass') or '')
            hay = f"{t} {b.get('varname','')} {b.get('maxclass','')}".lower()
            if ql in hay:
                print(f"  [{sp}] id={b.get('id'):>10}  varname={b.get('varname','-'):<22} {b.get('maxclass',''):<12} :: {t[:90]}")
