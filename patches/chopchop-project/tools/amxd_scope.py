"""Dump a named subpatcher scope: its boxes and internal patchlines."""
import json, sys
from amxd_extract import extract

def find_scope(patcher, name):
    for b in patcher.get('boxes', []):
        bb = b.get('box', b)
        t = (bb.get('text') or '')
        if bb.get('patcher') and (t == name or t.replace('p ','') == name.replace('p ','')):
            return bb['patcher']
        if bb.get('patcher'):
            r = find_scope(bb['patcher'], name)
            if r: return r
    return None

p = extract(sys.argv[1])
pat = p.get('patcher', p)
scope = find_scope(pat, sys.argv[2]) if len(sys.argv) > 2 else pat
if scope is None:
    print('scope not found'); sys.exit(1)

boxes = {}
for b in scope.get('boxes', []):
    bb = b.get('box', b)
    boxes[bb.get('id')] = bb
    t = bb.get('text') or bb.get('maxclass')
    extra = ''
    for k in ('varname','numinlets','numoutlets'):
        if bb.get(k) not in (None,''): extra += f' {k}={bb.get(k)}'
    inner = ' [+subpatcher]' if bb.get('patcher') else ''
    print(f"{bb.get('id'):>12}  {t}{extra}{inner}")
print('--- lines ---')
for l in scope.get('lines', []):
    ll = l.get('patchline', l)
    s = ll.get('source'); d = ll.get('destination')
    st = (boxes.get(s[0],{}).get('text') or boxes.get(s[0],{}).get('maxclass') or s[0])
    dt = (boxes.get(d[0],{}).get('text') or boxes.get(d[0],{}).get('maxclass') or d[0])
    print(f"  {st}  [{s[1]}] -> [{d[1]}]  {dt}")
