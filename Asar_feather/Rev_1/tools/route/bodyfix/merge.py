"""Body-collision fixes (2026-11-19, docs/body_fixes.md): merge the three verified fix plans into one emit_copper plan.

    python tools/route/bodyfix/merge.py

  btn/plan.json    BTN 0.50 mm west, away from X5's housing (N$BTN and N$LD0B re-laid on Top)
  c151/plan.json   C151 0.50 mm east, off U8's body corner (the VU through via moves into C147-2, a via-in-pad)
  x2row/plan.json  C40 C41 C152 C153 C154 R19 C155-C159 C38 0.125 mm north, out from under X2's bottom header housing;
                   R18 (+0.02, +0.05) opens the TDI lane; vias stay, Bottom jogs to the moved pads

Each plan was designed and independently verified from model0.json (the saved board c4bf0b71, route_model.py) in
the 2026-11-19 workflow wf_15b49ce3-839. This script checks they share no item, adds each move's new origin (x, y,
from the PcbDoc's Components6) and pad-1 position, and writes plan.json, model_moved.json (pads moved, copper as
saved: route_check's base) and model_final.json (everything applied: body_check's input).
"""
import copy
import hashlib
import json
import os

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
PCB = os.path.join(os.path.dirname(TOOLS), 'Asar_feather.PrjPcb', 'asar_feather.PcbDoc')
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
PARTS = ['btn', 'c151', 'x2row']


def origins():
    f = olefile.OleFileIO(PCB)
    out = {}
    for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)):
        if 'PATTERN=' in r:
            kv = dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x)
            out[kv['SOURCEDESIGNATOR']] = (float(kv['X'].replace('mil', '')) * 0.0254, float(kv['Y'].replace('mil', '')) * 0.0254)
    return out


def tkey(t):
    a, b = (round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))
    return (t['net'], t['layer'], round(t['w'], 4)) + tuple(sorted([a, b]))


def vkey(v):
    sp = v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
    return (v['net'], round(v['x'], 4), round(v['y'], 4), round(v['hole'], 4), sp[0], sp[-1])


def main():
    M0 = json.load(open(os.path.join(HERE, 'model0.json')))
    assert hashlib.md5(open(PCB, 'rb').read()).hexdigest() == 'c4bf0b71cc7362c33762083bf29810b1', 'board changed'
    plans = {k: json.load(open(os.path.join(HERE, k, 'plan.json'))) for k in PARTS}
    plan = {'moves': [], 'remove': [], 'remove_vias': [], 'tracks': [], 'vias': []}
    seen = {}
    for k in PARTS:
        for f in plan:
            for o in plans[k].get(f, []):
                key = (f, o['ref']) if f == 'moves' else (f, tkey(o) if f in ('remove', 'tracks') else vkey(o))
                assert key not in seen, ('shared item', key, seen.get(key), k)
                seen[key] = k
                plan[f].append(dict(o))
    base_t = {tkey(t) for t in M0['tracks']}
    base_v = {vkey(v) for v in M0['vias']}
    assert all(tkey(t) in base_t for t in plan['remove']), 'a removed track is not on the board'
    assert all(vkey(v) in base_v for v in plan['remove_vias']), 'a removed via is not on the board'

    O = origins()
    D = {m['ref']: (m['dx'], m['dy']) for m in plan['moves']}
    MM = copy.deepcopy(M0)
    for p in MM['pads']:
        if p['ref'] in D:
            p['x'], p['y'] = round(p['x'] + D[p['ref']][0], 4), round(p['y'] + D[p['ref']][1], 4)
    for m in plan['moves']:
        ox, oy = O[m['ref']]
        m['x'], m['y'] = round(ox + m['dx'], 4), round(oy + m['dy'], 4)
        p1 = [p for p in MM['pads'] if p['ref'] == m['ref'] and p['pad'] == '1']
        assert len(p1) == 1, m['ref']
        m['pad1'] = [p1[0]['x'], p1[0]['y']]
    json.dump(MM, open(os.path.join(HERE, 'model_moved.json'), 'w'))

    MF = copy.deepcopy(MM)
    rt = {tkey(t) for t in plan['remove']}
    rv = {vkey(v) for v in plan['remove_vias']}
    MF['tracks'] = [t for t in MF['tracks'] if tkey(t) not in rt] + [dict(t) for t in plan['tracks']]
    MF['vias'] = [v for v in MF['vias'] if vkey(v) not in rv] + [
        dict({q: v[q] for q in v if q not in ('from', 'to')}, span=STACK[STACK.index(v['from']):STACK.index(v['to']) + 1])
        for v in plan['vias']]
    json.dump(MF, open(os.path.join(HERE, 'model_final.json'), 'w'))
    json.dump(plan, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)
    print('%d moves, remove %d tracks + %d vias, add %d tracks + %d vias' % (
        len(plan['moves']), len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias'])))
    for m in plan['moves']:
        print('  %-5s (%+.3f, %+.3f) -> origin (%.4f, %.4f), pad 1 (%.4f, %.4f)' % (
            m['ref'], m['dx'], m['dy'], m['x'], m['y'], m['pad1'][0], m['pad1'][1]))


if __name__ == '__main__':
    main()
