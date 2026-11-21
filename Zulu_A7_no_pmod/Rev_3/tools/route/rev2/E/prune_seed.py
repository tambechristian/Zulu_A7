"""prune_seed.py <model.json> <seed.json> <rip.json> <out_model> <out_seed> <out_rip> [x0,y0,x1,y1]
Dead copper (prune_stubs.analyse on model + seed) of fully connected nets is dropped before routing on (optionally
only inside a box): dead seed items leave the seed, dead model (board) items leave the model and join the rip.
Per net, the drop is kept only if that net's island count does not grow (prune_stubs' centreline join test can
call an off-centre T-join dead). Trimmed tracks are left alone."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
import prune_stubs as PS
M0, S, RP = E.load(sys.argv[1]), E.load(sys.argv[2]), E.load(sys.argv[3])
box = tuple(map(float, sys.argv[7].split(','))) if len(sys.argv) > 7 else None
inb = lambda x, y: box is None or (box[0] <= x <= box[2] and box[1] <= y <= box[3])
sv = [dict(v, span=E.span(v)) for v in S['vias']]
M = dict(M0, tracks=M0['tracks'] + S['tracks'], vias=M0['vias'] + sv)
I0 = E.C.islands(M)
openn = {k for k, v in E.C.open_count(I0).items() if v}
dt, dv, nt, nv = PS.analyse(M)
dt = [t for t in dt if t['net'] not in openn and (inb(t['x1'], t['y1']) or inb(t['x2'], t['y2']))]
dv = [v for v in dv if v['net'] not in openn and inb(v['x'], v['y'])]
nets = sorted({t['net'] for t in dt} | {v['net'] for v in dv})
keep_t, keep_v = [], []
for n in nets:
    tk = {E.tkey(t) for t in dt if t['net'] == n}
    vk = {E.vkey(v) for v in dv if v['net'] == n}
    Mn = dict(M, pads=M['pads'], tracks=[t for t in M['tracks'] if t['net'] == n and E.tkey(t) not in tk],
              vias=[v for v in M['vias'] if v['net'] == n and E.vkey(v) not in vk])
    k1 = len(E.C.islands(Mn).get(n, []))
    if k1 <= len(I0.get(n, [])):
        keep_t += [t for t in dt if t['net'] == n]
        keep_v += [v for v in dv if v['net'] == n]
    else:
        print('  skip %s (pruning would split it: %d -> %d islands)' % (n, len(I0.get(n, [])), k1))
dtk, dvk = {E.tkey(t) for t in keep_t}, {E.vkey(v) for v in keep_v}
stk, svk = {E.tkey(t) for t in S['tracks']}, {E.vkey(v) for v in sv}
base_dt = [t for t in M0['tracks'] if E.tkey(t) in dtk and E.tkey(t) not in stk]
base_dv = [v for v in M0['vias'] if E.vkey(v) in dvk and E.vkey(v) not in svk]
M1 = E.apply(M0, base_dt, base_dv)
S1 = dict(S, tracks=[t for t in S['tracks'] if E.tkey(t) not in dtk], vias=[v for v in S['vias'] if E.vkey(v) not in dvk])
R1 = {'remove': RP['remove'] + base_dt, 'remove_vias': RP['remove_vias'] + base_dv}
E.dump(M1, sys.argv[4]); E.dump(S1, sys.argv[5], 0); E.dump(R1, sys.argv[6], 0)
from collections import Counter
print('dropped: %d tracks %d vias (%d / %d board items)' % (len(keep_t), len(keep_v), len(base_dt), len(base_dv)))
print(' by net', dict(Counter(t['net'] for t in keep_t) + Counter(v['net'] for v in keep_v)))
M2 = dict(M1, tracks=M1['tracks'] + S1['tracks'], vias=M1['vias'] + [dict(v, span=E.span(v)) for v in S1['vias']])
oc = E.C.open_count(E.C.islands(M2))
print('open after', sum(oc.values()), {k: v for k, v in oc.items() if v})
