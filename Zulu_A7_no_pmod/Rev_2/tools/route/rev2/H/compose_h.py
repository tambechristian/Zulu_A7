"""compose_h.py <router_plan.json> <tag> [extra_plan.json ...]
Strategy H composer: usb_fixed + router plan (+ extra hand plans, whose 'remove'/'remove_vias' add to the rip)
against prep/base_moved with rip_H -> aug_h.fix_all (joints prune_stubs would not accept are trimmed / connected,
dead tails dropped) -> compose_plan (prune to 0 dead copper) -> finalize (cancel remove/add pairs) -> final_<tag>.json
and board_<tag>.json. Prints the router-view open count and the composed open count (they must agree)."""
import json
import subprocess
import sys

H = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/route/rev2/H/'
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/'
sys.path.insert(0, T)
sys.path.insert(0, H)
import compose_plan as CP  # noqa: E402
import route_conn as C  # noqa: E402
import aug_h  # noqa: E402

base = json.load(open(H + '../prep/base_moved.json'))
rip = json.load(open(H + 'rip_H.json'))
usb = json.load(open(H + 'usb_fixed.json'))
rp = json.load(open(sys.argv[1]))
tag = sys.argv[2]
extra = [json.load(open(f)) for f in sys.argv[3:]]
plus_t = usb['tracks'] + rp['tracks'] + [t for e in extra for t in e.get('tracks', [])]
plus_v = usb['vias'] + rp['vias'] + [v for e in extra for v in e.get('vias', [])]
rm_t = list(rip['remove']) + [t for e in extra for t in e.get('remove', [])]
rm_v = list(rip['remove_vias']) + [v for e in extra for v in e.get('remove_vias', [])]
M0 = CP.apply(base, {'remove': rm_t, 'remove_vias': rm_v, 'tracks': plus_t, 'vias': plus_v})
oc0 = C.open_count(C.islands(M0))
print('router view open %d %s' % (sum(oc0.values()), dict(sorted(oc0.items()))))
lg = []
removed, added = aug_h.fix_all(M0['tracks'], M0['pads'], M0['vias'], log=lg)
for l in lg:
    if not l.startswith('dead'):
        print('  ' + l)
print('fix_all: %d tracks changed/dropped, %d tracks added (%d dead tails dropped)' % (
    len(removed), len(added), sum(1 for l in lg if l.startswith('dead'))))
pk = {}
for t in plus_t:
    pk.setdefault(CP.tkey(t), []).append(t)
bk = {CP.tkey(t) for t in base['tracks']}
drop_plan = set()
for t in removed:
    k = CP.tkey(t)
    if pk.get(k):
        drop_plan.add(k)
    if k in bk:
        rm_t.append(t)
plus_t = [t for t in plus_t if CP.tkey(t) not in drop_plan] + added
plus = {'tracks': plus_t, 'vias': plus_v, 'remove': [], 'remove_vias': []}
json.dump(plus, open(H + 'plus_%s.json' % tag, 'w'))
json.dump({'remove': rm_t, 'remove_vias': rm_v}, open(H + 'rip_%s.json' % tag, 'w'))
Mf = CP.apply(base, {'remove': rm_t, 'remove_vias': rm_v, 'tracks': plus_t, 'vias': plus_v})
ocf = C.open_count(C.islands(Mf))
print('after fix_all open %d %s' % (sum(ocf.values()), {n: v for n, v in ocf.items() if v > oc0.get(n, 0)}))
r = subprocess.run([sys.executable, T + 'compose_plan.py', H + '../prep/base_moved.json', H + 'rip_%s.json' % tag,
                    H + 'plus_%s.json' % tag, H + 'comp_%s.json' % tag], capture_output=True, text=True)
print(r.stdout[-1500:], r.stderr[-1500:])
r = subprocess.run([sys.executable, H + 'finalize.py', H + 'comp_%s.json' % tag, H + 'final_%s.json' % tag],
                   capture_output=True, text=True)
print(r.stdout, r.stderr[-1500:])
F = json.load(open(H + 'final_%s.json' % tag))
# dedupe: identical added tracks / vias, and added copies of board copper that stays
rmk = {CP.tkey(t) for t in F['remove']}
rmv = {CP.vkey(v) for v in F['remove_vias']}
keep_bt = {CP.tkey(t) for t in base['tracks'] if CP.tkey(t) not in rmk}
keep_bv = {CP.vkey(v) + (round(v['size'], 3),) for v in base['vias'] if CP.vkey(v) not in rmv}
def ukey(t):        # direction-free key: a reversed copy is the same copper
    a, b = (round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))
    return (t['net'], t['layer'], min(a, b), max(a, b), round(t['w'], 3))


keep_bt |= {ukey(t) for t in base['tracks'] if CP.tkey(t) not in rmk}
seen, nt = set(), []
for t in F['tracks']:
    k = ukey(t)
    if k in seen or k in keep_bt or CP.tkey(t) in keep_bt:
        continue
    seen.add(k)
    nt.append(t)
seen, nv = set(), []
for v in F['vias']:
    k = CP.vkey(v) + (round(v['size'], 3),)
    if k in seen or k in keep_bv:
        continue
    seen.add(k)
    nv.append(v)
print('dedupe: tracks %d -> %d, vias %d -> %d' % (len(F['tracks']), len(nt), len(F['vias']), len(nv)))
F['tracks'], F['vias'] = nt, nv
json.dump(F, open(H + 'final_%s.json' % tag, 'w'), indent=1)
M1 = CP.apply(base, F)
oc1 = C.open_count(C.islands(M1))
print('composed open %d %s' % (sum(oc1.values()), dict(sorted(oc1.items()))))
print('REOPENED by compose:', {n: v for n, v in oc1.items() if v > oc0.get(n, 0)})
json.dump(M1, open(H + 'board_%s.json' % tag, 'w'))
