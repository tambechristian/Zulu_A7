"""clean_seed.py <model.json> <seed.json> <model_out.json> <seed_out.json> <extra_rip_out.json> [keep_nets]
Frees routing room before a router pass: on every net that is already CLOSED in model + seed (0 open connections),
dead copper (tails and vias that join nothing, as prune_stubs judges after aug_h's joint repair) is removed, from the
seed (router copper) and from the model (board copper: written to extra_rip_out as {remove, remove_vias} so the
composer takes it off the board too). Open nets keep their partial routes. Joint repairs that ADD a connector or trim
a track are applied too (they change no clearance)."""
import json
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/H')
import compose_plan as CP  # noqa: E402
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402
import aug_h  # noqa: E402

STACK = CP.STACK
M = json.load(open(sys.argv[1]))
S = json.load(open(sys.argv[2]))
keep = set(sys.argv[6].split(',')) if len(sys.argv) > 6 else set()
for t in M['tracks']:
    t['_src'] = 'm'
for v in M['vias']:
    v['_src'] = 'm'
tracks = M['tracks'] + [dict(t, _src='s') for t in S['tracks']]
vias = M['vias'] + [dict(v, span=CP.vspan(v), _src='s') for v in S['vias']]
Mx = dict(M, tracks=tracks, vias=vias)
oc = C.open_count(C.islands(Mx))
nets = {t['net'] for t in tracks} | {v['net'] for v in vias}
closed = {n for n in nets if oc.get(n, 0) == 0 and n not in keep}
print('open %d on %d nets; cleaning %d closed nets' % (sum(oc.values()), len(oc), len(closed)))
rm_m_t, rm_m_v = [], []
for it in range(10):
    removed, added = aug_h.fix_all(tracks, M['pads'], vias, nets=closed)
    rid = {id(t) for t in removed}
    for t in removed:
        if t['_src'] == 'm':
            rm_m_t.append(t)
    tracks = [t for t in tracks if id(t) not in rid] + [dict(t, _src='s') for t in added]
    sub = dict(M, tracks=[t for t in tracks if t['net'] in closed], vias=[v for v in vias if v['net'] in closed])
    dt, dv, _, _ = PS.analyse(sub)
    dvid = {id(v) for v in dv}
    for v in dv:
        if v['_src'] == 'm':
            rm_m_v.append(v)
    vias = [v for v in vias if id(v) not in dvid]
    print('pass %d: %d tracks changed/dropped, %d added, %d dead vias' % (it + 1, len(removed), len(added), len(dv)))
    if not removed and not added and not dv:
        break
Mx = dict(M, tracks=tracks, vias=vias)
oc2 = C.open_count(C.islands(Mx))
print('open after clean %d %s' % (sum(oc2.values()), {n: v for n, v in oc2.items() if v > oc.get(n, 0)}))
strip = lambda d: {k: v for k, v in d.items() if k != '_src'}  # noqa: E731
Mo = dict(M, tracks=[strip(t) for t in tracks if t['_src'] == 'm'], vias=[strip(v) for v in vias if v['_src'] == 'm'])
json.dump(Mo, open(sys.argv[3], 'w'))
So = {'tracks': [strip(t) for t in tracks if t['_src'] == 's'],
      'vias': [{k: v for k, v in strip(x).items() if k != 'span'} | {'from': x['span'][0], 'to': x['span'][-1]}
               for x in vias if x['_src'] == 's'], 'remove': [], 'remove_vias': []}
json.dump(So, open(sys.argv[4], 'w'), indent=0)
json.dump({'remove': [strip(t) for t in rm_m_t], 'remove_vias': [strip(v) for v in rm_m_v]}, open(sys.argv[5], 'w'), indent=0)
print('model: -%d tracks -%d vias; seed %d -> %d tracks, %d -> %d vias' % (
    len(rm_m_t), len(rm_m_v), len(S['tracks']), len(So['tracks']), len(S['vias']), len(So['vias'])))
