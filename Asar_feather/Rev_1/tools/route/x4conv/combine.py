"""hand_plan + router plan -> pruned final plan (dead stubs of the touched nets removed).  python combine.py r1.json out.json"""
import json, sys, math
sys.path.insert(0, "C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools")
import route_conn as C
import plan_prune as PP
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
M0 = json.load(open('model0.json')); M1 = json.load(open('model1.json'))
H = json.load(open('hand_plan.json')); R = json.load(open(sys.argv[1]))
assert not R.get('remove') and not R.get('remove_vias')
def tkey(t): return (t['net'], t['layer'], round(t['w'], 4), frozenset([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))]))
def vkey(v): return (v['net'], round(v['x'], 3), round(v['y'], 3), round(v['hole'], 3), tuple(v.get('span') or S[S.index(v['from']):S.index(v['to']) + 1]))
rm_t = {tkey(t) for t in H['remove']}; rm_v = {vkey(v) for v in H['remove_vias']}
base_t = [t for t in M0['tracks'] if tkey(t) not in rm_t]
base_v = [dict(v) for v in M0['vias'] if vkey(v) not in rm_v]
assert len(M0['tracks']) - len(base_t) == len(H['remove']), (len(M0['tracks']) - len(base_t), len(H['remove']))
assert len(M0['vias']) - len(base_v) == len(H['remove_vias'])
new_t = [dict(t, _new=1) for t in H['tracks'] + R['tracks']]
new_v = [dict({k: v[k] for k in v if k not in ('from', 'to', 'span')}, span=list(v.get('span') or S[S.index(v['from']):S.index(v['to']) + 1]), _new=1) for v in H['vias'] + R['vias']]
NETS = ['VBATT', 'VU', 'GND', 'VCC3V3', 'EE-CS', 'EE-CLK', 'EE-DATA', 'EE-DATA-DO']
BOX = (2.0, 9.0, 19.0, 22.86)
inb = lambda x, y: BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3]
plane_of = {net: lay for lay, net in M1['planes'].items()}
final_t, final_v = [t for t in base_t if t['net'] not in NETS], [v for v in base_v if v['net'] not in NETS]
log = []
for net in NETS:
    pads = [p for p in M1['pads'] if p['net'] == net]
    allt = [t for t in base_t if t['net'] == net] + [t for t in new_t if t['net'] == net]
    allv = [v for v in base_v if v['net'] == net] + [v for v in new_v if v['net'] == net]
    mov_t = [t for t in allt if inb(t['x1'], t['y1']) or inb(t['x2'], t['y2'])]
    mov_v = [v for v in allv if inb(v['x'], v['y'])]
    fix_t = [t for t in allt if t not in mov_t]; fix_v = [v for v in allv if v not in mov_v]
    nt, nv = PP.prune_net(net, pads, fix_t, fix_v, mov_t, mov_v, plane_of.get(net))
    # prune_net drops 'span' and '_new' survives in dicts; restore spans
    nv2, j = [], 0                       # prune_net keeps the survivors in order and drops 'span': match them in order
    for v in nv:
        while not (abs(mov_v[j]['x'] - v['x']) < 1e-9 and abs(mov_v[j]['y'] - v['y']) < 1e-9 and mov_v[j]['hole'] == v['hole'] and mov_v[j]['size'] == v['size']):
            j += 1
        nv2.append(dict(v, span=mov_v[j]['span'])); j += 1
    log.append('%s: movable %d tracks / %d vias -> %d / %d' % (net, len(mov_t), len(mov_v), len(nt), len(nv2)))
    final_t += fix_t + nt; final_v += fix_v + nv2
# islands check on the final copper with the new pads
Mf = dict(M1, tracks=[{k: t[k] for k in t if k != '_new'} for t in final_t], vias=[{k: v[k] for k in v if k != '_new'} for v in final_v])
I = C.islands(Mf)
op = {n: len([g for g in v if g['pads']]) - 1 for n, v in I.items()}
op = {n: c for n, c in op.items() if c > 0}
dead = {n: len([g for g in v if not g['pads']]) for n, v in I.items() if any(not g['pads'] for g in v) and n in NETS}
print('\n'.join(log)); print('open after:', op, ' pad-less islands in touched nets:', dead)
# express as a plan against M0: remove = M0 copper absent from final; add = final copper absent from M0
f_t = {tkey(t) for t in final_t}; f_v = {vkey(v) for v in final_v}
m_t = {tkey(t) for t in M0['tracks']}; m_v = {vkey(v) for v in M0['vias']}
plan = dict(remove=[t for t in M0['tracks'] if tkey(t) not in f_t],
            remove_vias=[v for v in M0['vias'] if vkey(v) not in f_v],
            tracks=[{k: t[k] for k in ('net', 'layer', 'w', 'x1', 'y1', 'x2', 'y2')} for t in final_t if tkey(t) not in m_t],
            vias=[])
for v in final_v:
    if vkey(v) not in m_v:
        sp = v['span']
        plan['vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=sp, **{'from': sp[0], 'to': sp[-1]}))
# a removal is matched on the board by (net, x, y, hole): keep every via of a stack whose siblings stay
keep = []
for r in plan['remove_vias']:
    sib = [v for v in M0['vias'] if v['net'] == r['net'] and abs(v['x'] - r['x']) < 0.002 and abs(v['y'] - r['y']) < 0.002 and abs(v['hole'] - r['hole']) < 0.002]
    if not all(any(vkey(s) == vkey(q) for q in plan['remove_vias']) for s in sib):
        keep.append(r)
if keep:
    print('kept (stack siblings stay):', [(r['net'], r['x'], r['y'], r['span'][0], r['span'][-1]) for r in keep])
plan['remove_vias'] = [r for r in plan['remove_vias'] if r not in keep]
json.dump(plan, open(sys.argv[2], 'w'), indent=0)
from collections import Counter
print('plan: remove %d tracks %s, %d vias %s; add %d tracks %s, %d vias %s' % (
    len(plan['remove']), dict(Counter(t['net'] for t in plan['remove'])), len(plan['remove_vias']), dict(Counter(v['net'] for v in plan['remove_vias'])),
    len(plan['tracks']), dict(Counter(t['net'] for t in plan['tracks'])), len(plan['vias']), dict(Counter(v['net'] for v in plan['vias']))))
