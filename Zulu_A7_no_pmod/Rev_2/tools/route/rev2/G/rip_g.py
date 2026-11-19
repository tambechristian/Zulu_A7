"""rip_g.py <base_moved.json> <prep_rip.json> <out_rip.json> [extra_rip.json ...]
Strategy G minimal rip: instead of prep's rule 1 (every track / via of a moved pad's signal net inside a 29 x 25 mm
window), only copper that really clashes with a moved land is ripped, judged with exact geometry (route_conn's
round / rect pads) and the router's clearances:
  a. any track / via of another net closer than clearance(net, layer) to a moved land on a shared layer;
  b. any via whose hole comes within 0.24 mm of a moved drilled pad's hole (any net);
  c. GND / VCC3V3 tracks ending on an OLD land of a moved pad and plane vias inside an old land (prep rule 3);
  d. all USB_D_P / USB_D_N copper (the pair is rebuilt by hand);
  e. whole via columns of any ripped via (prep rule 4);
  f. whatever the extra rip files list (hand-route clearances).
Old copper of a moved pad's own net that does not clash is KEPT (it dangles at the old land until a connector from
the new land joins it; compose_plan prunes what stays dead).
Prints which prep-rip items are kept and the open count of base - rip."""
import json
import math
import os
import sys

T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0, T)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402
import compose_plan as CP  # noqa: E402

STACK = R.STACK
PLANE = {'GND', 'VCC3V3'}
MOVES = {'X1': (-2.54, 0.0), 'X4': (-2.54, 0.0), 'U10': (-1.3, -0.05), 'R96': (-0.9, 1.2), 'R84': (-1.7, 0.6),
         'R86': (-1.7, 0.6)}
PAD_MOVES = {('X2', '10'): (10.16, 0.0), ('X2', '30'): (10.16, 0.0)}
REBUILD = {'USB_D_P', 'USB_D_N'}


def pad_layers(p):
    return p['layers'] if p['layers'] else (STACK if p['drill'] else [])


def main():
    B = json.load(open(sys.argv[1]))
    prep = json.load(open(sys.argv[2]))
    new, old = [], []
    for p in B['pads']:
        d = MOVES.get(p['ref']) or PAD_MOVES.get((p['ref'], p['pad']))
        if d:
            new.append(p)
            q = dict(p)
            q['x'] = round(p['x'] - d[0], 4)
            q['y'] = round(p['y'] - d[1], 4)
            old.append(q)
    rm_t, rm_v = set(), set()
    why = {}
    for i, t in enumerate(B['tracks']):
        if t['net'] in REBUILD:
            rm_t.add(i); why[('t', i)] = 'rebuild'
            continue
        s = (t['x1'], t['y1'], t['x2'], t['y2'])
        for p in new:
            if t['net'] == p['net'] or t['layer'] not in pad_layers(p):
                continue
            need = max(R.clearance(t['net'], t['layer']), R.clearance(p['net'] or '', t['layer']))
            if C.pad_seg(p, s) - t['w'] / 2 < need - 1e-4:
                rm_t.add(i); why[('t', i)] = 'clash %s-%s' % (p['ref'], p['pad'])
                break
        else:
            if t['net'] in PLANE:
                for p in old:
                    if p['net'] == t['net'] and t['layer'] in pad_layers(p) and (
                            C.pad_point(p, t['x1'], t['y1']) <= 0 or C.pad_point(p, t['x2'], t['y2']) <= 0):
                        rm_t.add(i); why[('t', i)] = 'old land %s-%s' % (p['ref'], p['pad'])
                        break
    for i, v in enumerate(B['vias']):
        if v['net'] in REBUILD:
            rm_v.add(i); why[('v', i)] = 'rebuild'
            continue
        for p in new:
            if not set(v['span']) & set(pad_layers(p)):
                continue
            if v['net'] != p['net']:
                for l in set(v['span']) & set(pad_layers(p)):
                    need = max(R.clearance(v['net'], l), R.clearance(p['net'] or '', l))
                    if C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < need - 1e-4:
                        rm_v.add(i); why[('v', i)] = 'clash %s-%s' % (p['ref'], p['pad'])
                        break
            if i in rm_v:
                break
            if p['drill'] and math.hypot(v['x'] - p['x'], v['y'] - p['y']) - v['hole'] / 2 - p['drill'] / 2 < R.HOLE_HOLE - 1e-4:
                rm_v.add(i); why[('v', i)] = 'hole %s-%s' % (p['ref'], p['pad'])
                break
        else:
            if v['net'] in PLANE:
                for p in old:
                    if p['net'] == v['net'] and set(v['span']) & set(pad_layers(p)) and C.pad_point(p, v['x'], v['y']) <= 0:
                        rm_v.add(i); why[('v', i)] = 'old land %s-%s' % (p['ref'], p['pad'])
                        break
    for f in sys.argv[4:]:
        X = json.load(open(f))
        xt = {CP.tkey(t) for t in X.get('remove', [])}
        xv = {CP.vkey(v) for v in X.get('remove_vias', [])}
        nt = nv = 0
        for i, t in enumerate(B['tracks']):
            if CP.tkey(t) in xt:
                rm_t.add(i); why.setdefault(('t', i), 'extra'); nt += 1
        for i, v in enumerate(B['vias']):
            if CP.vkey(v) in xv:
                rm_v.add(i); why.setdefault(('v', i), 'extra'); nv += 1
        if nt != len(xt) or nv != len(xv):
            print('WARNING %s: matched %d/%d tracks %d/%d vias' % (f, nt, len(xt), nv, len(xv)))
    cols = {(B['vias'][i]['net'], round(B['vias'][i]['x'], 4), round(B['vias'][i]['y'], 4)) for i in rm_v}
    for i, v in enumerate(B['vias']):
        if (v['net'], round(v['x'], 4), round(v['y'], 4)) in cols and i not in rm_v:
            rm_v.add(i); why[('v', i)] = 'column'
    rip = {'remove': [B['tracks'][i] for i in sorted(rm_t)], 'remove_vias': [B['vias'][i] for i in sorted(rm_v)]}
    json.dump(rip, open(sys.argv[3], 'w'), indent=0)
    pk = {CP.tkey(t) for t in prep['remove']}
    pv = {CP.vkey(v) for v in prep['remove_vias']}
    mine_t = {CP.tkey(t) for t in rip['remove']}
    mine_v = {CP.vkey(v) for v in rip['remove_vias']}
    print('G rip: %d tracks, %d vias (prep: %d, %d); kept from prep: %d tracks %d vias; extra over prep: %d tracks %d vias' % (
        len(rm_t), len(rm_v), len(prep['remove']), len(prep['remove_vias']), len(pk - mine_t), len(pv - mine_v),
        len(mine_t - pk), len(mine_v - pv)))
    for i in sorted(rm_t):
        t = B['tracks'][i]
        if CP.tkey(t) not in pk:
            print('  extra T %-10s %-12s (%.3f,%.3f)-(%.3f,%.3f) %s' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'], why[('t', i)]))
    for i in sorted(rm_v):
        v = B['vias'][i]
        if CP.vkey(v) not in pv:
            print('  extra V %-10s (%.3f,%.3f) %s %s' % (v['net'], v['x'], v['y'], '>'.join(s[:2] for s in v['span']), why[('v', i)]))
    M = CP.apply(B, dict(rip, tracks=[], vias=[]))
    oc = C.open_count(C.islands(M))
    print('open after G rip: %d on %d nets: %s' % (sum(oc.values()), len(oc), ', '.join('%s %d' % kv for kv in sorted(oc.items(), key=lambda kv: -kv[1]))))
    if os.environ.get('WHY'):
        for (k, i), w in sorted(why.items()):
            o = B['tracks'][i] if k == 't' else B['vias'][i]
            print('  %s %s %s' % (k, o['net'], w), o.get('layer', ''), o.get('x1', o.get('x')), o.get('y1', o.get('y')))


if __name__ == '__main__':
    main()
