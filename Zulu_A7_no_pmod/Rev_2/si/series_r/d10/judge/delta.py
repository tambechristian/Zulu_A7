"""Exact delta of a plan JSON vs the 12-resistor dq_series_r_plan.json (set difference on rounded records).
Usage: python delta.py <plan.json> [tag]   -> prints, and writes delta_<tag>.json in this folder"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.normpath(os.path.join(HERE, '..', '..'))
A = json.load(open(os.path.join(SR, 'dq_series_r_plan.json')))
P = json.load(open(sys.argv[1]))
tag = sys.argv[2] if len(sys.argv) > 2 else 'plan'


def kt(t):
    e = sorted([(round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))])
    return (t['net'], t['layer'], round(t['w'], 4), tuple(e), t.get('why', ''))


def kv(v):
    return (v['net'], round(v['x'], 4), round(v['y'], 4), v.get('from', v.get('span', [''])[0]), v.get('to', v.get('span', [''])[-1]),
            round(v.get('size', 0), 3), round(v['hole'], 3), v.get('why', ''))


out = {}
for sec, f in (('remove', kt), ('tracks', kt), ('remove_vias', kv), ('vias', kv), ('microvias', kv)):
    a = {f(x) for x in A[sec]}
    b = {f(x) for x in P[sec]}
    out[sec] = dict(only_in_12R=sorted(a - b), only_in_plan=sorted(b - a))
pa = {p['ref']: p for p in A['parts']}
pb = {p['ref']: p for p in P['parts']}
parts = []
for r in sorted(set(pa) | set(pb)):
    if r not in pa:
        parts.append(('ADDED', r, pb[r]))
    elif r not in pb:
        parts.append(('REMOVED', r, pa[r]))
    elif json.dumps(pa[r], sort_keys=True) != json.dumps(pb[r], sort_keys=True):
        parts.append(('MOVED', r, dict(frm=(pa[r]['x'], pa[r]['y'], pa[r]['rot']), to=(pb[r]['x'], pb[r]['y'], pb[r]['rot']),
                                       pad1=(pb[r]['pad1']), pad2=(pb[r]['pad2']))))
out['parts'] = parts
ra = {(p['ref'], p['pad'], p['net']) for p in A['renet_pads']}
rb = {(p['ref'], p['pad'], p['net']) for p in P['renet_pads']}
out['renet_pads'] = dict(only_in_12R=sorted(ra - rb), only_in_plan=sorted(rb - ra))
out['net_class_add'] = dict(only_in_12R=sorted(set(A['net_class_add']['SDRAM_DATA']) - set(P['net_class_add']['SDRAM_DATA'])),
                            only_in_plan=sorted(set(P['net_class_add']['SDRAM_DATA']) - set(A['net_class_add']['SDRAM_DATA'])))
out['counts'] = {k: (len(A[k]), len(P[k])) for k in ('remove', 'tracks', 'remove_vias', 'vias', 'parts', 'renet_pads', 'microvias')}
for k, v in out.items():
    print('==', k)
    if isinstance(v, dict):
        for kk, vv in v.items():
            print('  ', kk, len(vv) if isinstance(vv, list) else vv)
            if isinstance(vv, list):
                for x in vv:
                    print('     ', x)
    else:
        for x in v:
            print('  ', x)
json.dump(out, open(os.path.join(HERE, 'delta_%s.json' % tag), 'w'), indent=1, default=str)
