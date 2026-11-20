"""Stage B: hand copper on top of stage A (jogs): FT-VCORE via nudge, FT-RESETN onto L4 with a via-in-pad at R19-1,
TDI east branch removed (for the router). Writes plan_b.json and model_b.json (model1 + plan_b) for the router."""
import copy
import json
import sys
from geo import *
import stage_a as A

M1 = A.M1
S = STACK


def span(f, t):
    return S[S.index(f):S.index(t) + 1]


rm_t, rm_v, add_t, add_v = [], [], list(A.jogs), []

# 1. FT-VCORE stack (14.500, 2.900) 45+5B -> (14.475, 2.900): C153-1 moved beside it (0.070 -> 0.095)
NX = 14.475
for sp in ('45', '5B'):
    v = A.find_v(M1, 'FT-VCORE', 14.5, 2.9, sp)
    rm_v.append(v)
    add_v.append(dict(net='FT-VCORE', x=NX, y=2.9, size=v['size'], hole=v['hole'], **{'from': v['span'][0], 'to': v['span'][-1]}))
t = A.find_t(M1, 'FT-VCORE', 'Bottom Layer', 14.375, 2.775, 14.5, 2.9)
rm_t.append(t)
add_t.append(dict(t, x2=NX) if t['x2'] == 14.5 else dict(t, x1=NX))
t = A.find_t(M1, 'FT-VCORE', 'L4-SIG', 14.5, 2.9, 15.35, 2.7)
rm_t.append(t)
add_t.append(dict(t, x1=NX) if t['x1'] == 14.5 else dict(t, x2=NX))

# 2. FT-RESETN: the Bottom run (14.725,3.425) -> R19-1 and its L4>Bottom stack go; L4 continues to a stack_bot in R19-1
for seg in [(14.725, 3.425, 15.15, 3.0), (15.15, 3.0, 16.675, 3.0), (16.675, 3.0, 16.725, 2.975), (16.725, 2.975, 16.75, 2.95),
            (16.75, 2.95, 16.875, 2.95), (16.875, 2.95, 16.975, 2.85), (16.975, 2.85, 17.15, 2.775)]:
    rm_t.append(A.find_t(M1, 'FT-RESETN', 'Bottom Layer', *seg))
for sp in ('45', '5B'):
    rm_v.append(A.find_v(M1, 'FT-RESETN', 14.725, 3.425, sp))
rx, ry = A.padc('R19', '1')
YL4 = 3.6
for a, b in [((14.725, 3.425), (14.9, YL4)), ((14.9, YL4), (rx, YL4)), ((rx, YL4), (rx, ry))]:
    add_t.append(dict(net='FT-RESETN', layer='L4-SIG', w=0.0762, x1=a[0], y1=a[1], x2=b[0], y2=b[1]))
for f, t_ in (('L4-SIG', 'L5-VCC3V3'), ('L5-VCC3V3', 'Bottom Layer')):
    add_v.append(dict(net='FT-RESETN', x=rx, y=ry, size=0.30, hole=0.15, **{'from': f, 'to': t_}))

# 3. TDI: the via under U2-17 and the Bottom run under C41 (left for the router / hand route)
TDI_RM_T = [('Top Layer', 9.825, 3.075, 9.85, 3.075), ('Bottom Layer', 9.825, 3.075, 10.025, 3.05),
            ('Bottom Layer', 10.025, 3.05, 10.825, 3.05), ('Bottom Layer', 10.825, 3.05, 11.05, 3.275)]
TDI_RM_V = [(9.825, 3.075)]


def tdi_removals(M):
    return [A.find_t(M, 'TDI', l, *s) for l, *s in TDI_RM_T], [A.find_v(M, 'TDI', x, y) for x, y in TDI_RM_V]


def apply(M, rm_t, rm_v, add_t, add_v):
    Mx = copy.deepcopy(M)
    it, iv = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    Mx['tracks'] = [t2 for t2, t0 in zip(Mx['tracks'], M['tracks']) if id(t0) not in it] + [dict(t) for t in add_t]
    Mx['vias'] = [v2 for v2, v0 in zip(Mx['vias'], M['vias']) if id(v0) not in iv] + [
        dict({k: v[k] for k in v if k not in ('from', 'to')}, span=span(v['from'], v['to'])) for v in add_v]
    return Mx


if __name__ == '__main__':
    tt, tv = tdi_removals(M1)
    plan = dict(remove=[dict(t) for t in rm_t + tt], remove_vias=[dict(v) for v in rm_v + tv], tracks=add_t, vias=add_v)
    json.dump(plan, open('plan_b.json', 'w'), indent=1)
    MB = apply(M1, rm_t + tt, rm_v + tv, add_t, add_v)
    json.dump(MB, open('model_b.json', 'w'))
    print('plan_b: remove %d tracks %d vias, add %d tracks %d vias' % (len(plan['remove']), len(plan['remove_vias']),
                                                                       len(add_t), len(add_v)))
