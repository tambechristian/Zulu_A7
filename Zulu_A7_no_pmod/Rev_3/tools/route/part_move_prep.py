"""Move one SMD part by (dx, dy) and keep its routing (2026-11-19; generalises route/u4_move/prep.py).

    python tools/route/part_move_prep.py <board model.json> <out dir> REF DX DY [REF DX DY ...]

Every pad keeps its own fan-out: a jog on the pad's layer from the old pad centre to the new one (as wide as the
narrowest track that ends on the pad, at most the pad's short side). Other-net copper too close (0.09 mm) to a new
pad or jog, on that layer, is ripped and left to tools/router.py; a ripped via takes its stack partners with it.
Writes model.json (router input), base_moved.json (for compose_plan / route_check) and rip.json (moves + jogs).
The part origin is read from the PcbDoc (Components6) so emit_copper can check it before moving.
"""
import json
import os
import sys

import olefile

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
from bodies_fix_prep import pad_pt, pad_seg  # noqa: E402

CLR = 0.09
PCB = os.path.join(os.path.dirname(TOOLS), 'Imported zulu_a7.PrjPcb', 'Zulu_a7_no_pmod.PcbDoc')


def origin(ref):
    f = olefile.OleFileIO(PCB)
    for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)):
        if 'SOURCEDESIGNATOR=%s|' % ref in r:
            kv = dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x)
            return float(kv['X'].replace('mil', '')) * 0.0254, float(kv['Y'].replace('mil', '')) * 0.0254
    raise SystemExit('no component %s' % ref)


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    args = sys.argv[3:]
    moves_in = [(args[i], float(args[i + 1]), float(args[i + 2])) for i in range(0, len(args), 3)]
    os.makedirs(out, exist_ok=True)
    D = {r: (dx, dy) for r, dx, dy in moves_in}
    old = [dict(p) for p in M['pads'] if p['ref'] in D]
    assert old and all(not p['drill'] for p in old), 'SMD parts only'
    for p in M['pads']:
        if p['ref'] in D:
            dx, dy = D[p['ref']]
            p['x'], p['y'] = round(p['x'] + dx, 4), round(p['y'] + dy, 4)
    json.dump(M, open(os.path.join(out, 'base_moved.json'), 'w'))
    new = [p for p in M['pads'] if p['ref'] in D]
    jogs = []
    for p in old:
        dx, dy = D[p['ref']]
        L = p['layers'][0]
        ws = [t['w'] for t in M['tracks'] if t['net'] == p['net'] and t['layer'] == L and
              any(abs(x - p['x']) < 1e-3 and abs(y - p['y']) < 1e-3 for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])))]
        jogs.append({'net': p['net'], 'layer': L, 'w': min(ws + [min(p['w'], p['h'])]) if ws else 0.0762,
                     'x1': p['x'], 'y1': p['y'], 'x2': round(p['x'] + dx, 4), 'y2': round(p['y'] + dy, 4)})
    rm_t, rm_v = [], []
    for p in new:
        L = p['layers'][0]
        for t in M['tracks']:
            if t['layer'] == L and t['net'] != p['net'] and pad_seg(p, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
        for v in M['vias']:
            if L in v['span'] and v['net'] != p['net'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR and v not in rm_v:
                rm_v.append(v)
    for j in jogs:
        jp = {'x': (j['x1'] + j['x2']) / 2, 'y': (j['y1'] + j['y2']) / 2, 'w': abs(j['x2'] - j['x1']) + j['w'],
              'h': abs(j['y2'] - j['y1']) + j['w'], 'shape': 'rect'}
        for t in M['tracks']:
            if t['layer'] == j['layer'] and t['net'] != j['net'] and pad_seg(jp, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
        for v in M['vias']:
            if j['layer'] in v['span'] and v['net'] != j['net'] and pad_pt(jp, v['x'], v['y']) < v['size'] / 2 + CLR and v not in rm_v:
                rm_v.append(v)
    for v in list(rm_v):
        for w in M['vias']:
            if w is not v and w not in rm_v and abs(w['x'] - v['x']) < 1e-4 and abs(w['y'] - v['y']) < 1e-4 and w['net'] == v['net']:
                rm_v.append(w)
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t] + jogs
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    moves = []
    for ref, dx, dy in moves_in:
        ox, oy = origin(ref)
        np_ = [p for p in new if p['ref'] == ref]
        p1 = [p for p in np_ if p['pad'] == '1'][0]
        moves.append({'ref': ref, 'x': round(ox + dx, 4), 'y': round(oy + dy, 4), 'dx': dx, 'dy': dy,
                      'pad1': [p1['x'], p1['y']], 'pad_xy': {p['pad']: [p['x'], p['y']] for p in np_}})
        print('%s (%+.2f, %+.2f): origin (%.4f, %.4f)' % (ref, dx, dy, ox, oy))
    json.dump(M, open(os.path.join(out, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves, 'jogs': jogs}, open(os.path.join(out, 'rip.json'), 'w'), indent=1)
    nets = sorted({o['net'] for o in rm_t + rm_v})
    print('removed %d tracks, %d vias on %d nets: %s' % (len(rm_t), len(rm_v), len(nets), nets))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), dict(oc)))


if __name__ == '__main__':
    main()
