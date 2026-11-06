# -*- coding: utf-8 -*-
"""Independent checks of the FINAL stage-5 plan, not using gen.py's working.

    python tools/stage5/verify.py tools/stage5_route.json [--inputs PRE.json]

MUST be run against the board as it stood BEFORE stage 5 was placed -- the plan is expressed as
removals of copper that is no longer there once it is placed.  Since 2026-09-24 the default
tools/route_inputs.json IS the placed board, so pass --inputs with the pre-stage-5 model:

    git show 14a8511:Zulu_Altrium/tools/route_inputs.json > PRE.json
    python tools/stage5/verify.py tools/stage5_route.json --inputs PRE.json     -> 18 of 18

Run against the placed board it reports two spurious failures and nothing else -- the inventory
check (289 + 140 != 354) and the collinear-overlap check (the plan's tracks now also exist on the
board, so every one of them pairs with itself).  The guard below refuses that board outright
rather than letting anyone read those two as real."""
import io, json, math, os, sys, itertools, collections
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage5')
from lib import INP0

# the pre-stage-5 board has VCC3V3 at 354 tracks / 51 vias; the placed board has 163 / 81
_nt = sum(1 for t in INP0['tracks'] if t['net'] == 'VCC3V3')
_nv = sum(1 for v in INP0['vias'] if v['net'] == 'VCC3V3')
if (_nt, _nv) != (354, 51):
    sys.exit('verify.py: this is not the pre-stage-5 board (VCC3V3 has %d tracks and %d vias, the '
             'pre-stage-5 board has 354 and 51).  This script checks a plan expressed as removals, '
             'so it needs the board those removals still match:\n'
             '    git show 14a8511:Zulu_Altrium/tools/route_inputs.json > PRE.json\n'
             '    python tools/stage5/verify.py tools/stage5_route.json --inputs PRE.json' % (_nt, _nv))

PLAN = sys.argv[1] if len(sys.argv) > 1 else 'plan.json'
P = json.load(io.open(PLAN, encoding='utf-8'))
NET = 'VCC3V3'
LF = INP0['land_field']
ok, bad = [], []


def chk(c, msg, det=''):
    (ok if c else bad).append('%-58s %s' % (msg, det))


tracks, vias = INP0['tracks'], INP0['vias']
rk = lambda v: (round(v['x'], 4), round(v['y'], 4))
tk = lambda t: (t['net'], t['layer']) + tuple(sorted(((round(t['x1'], 4), round(t['y1'], 4)),
                                                      (round(t['x2'], 4), round(t['y2'], 4)))))
rt = {tk(t) for t in P['remove']['tracks']}
rv = {rk(v) for v in P['remove']['vias']}
btr = [t for t in tracks if t['net'] == NET]
bvi = [v for v in vias if v['net'] == NET]
kept_t = [t for t in btr if tk(t) not in rt]
kept_v = [v for v in bvi if rk(v) not in rv]
allt = kept_t + P['tracks']
allv = kept_v + P['vias']
pads = [dict(p, layer='Top') for p in INP0['top_pads']] + [dict(p, layer='Bottom') for p in INP0['bottom_pads']]
th = [dict(p, layer='Multi') for p in INP0['th_pads']]
own = [p for p in pads if p.get('net') == NET]
ownth = [p for p in th if p.get('net') == NET]

chk(all(t['net'] == NET for t in P['remove']['tracks']) and all(v['net'] == NET for v in P['remove']['vias']),
    'every removal is on net VCC3V3', '%d tracks, %d vias' % (len(rt), len(rv)))
chk(len(rt) + len(kept_t) == len(btr) and len(rv) + len(kept_v) == len(bvi),
    'removed + kept = the whole VCC3V3 inventory',
    '%d+%d=%d tracks, %d+%d=%d vias' % (len(rt), len(kept_t), len(btr), len(rv), len(kept_v), len(bvi)))

inf = lambda x, y: LF['x0'] <= x <= LF['x1'] and LF['y0'] <= y <= LF['y1']
chk(not [v for v in P['vias'] if inf(v['x'], v['y'])], 'no NEW via inside U1 land field', '')
chk(len([v for v in bvi if inf(v['x'], v['y'])]) == len([v for v in kept_v if inf(v['x'], v['y'])]),
    'all 14 in-field VCC3V3 vias kept', '%d kept' % len([v for v in kept_v if inf(v['x'], v['y'])]))

d = min((math.hypot(a['x'] - b['x'], a['y'] - b['y']), (a['x'], a['y']), (b['x'], b['y']))
        for a, b in itertools.product(P['vias'], vias)
        if not (abs(a['x'] - b['x']) < 1e-6 and abs(a['y'] - b['y']) < 1e-6))
d2 = min((math.hypot(a['x'] - b['x'], a['y'] - b['y']), (a['x'], a['y']), (b['x'], b['y']))
         for a, b in itertools.combinations(P['vias'], 2))
chk(d[0] >= 0.44 - 1e-6 and d2[0] >= 0.44 - 1e-6, 'every new via >= 0.44 mm from every other via',
    'closest new-to-board %.4f, new-to-new %.4f' % (d[0], d2[0]))

worst = (9.0, '')
for v in P['vias']:
    for p in pads:
        dx = max(0.0, abs(v['x'] - p['x']) - p['sx'] / 2.0)
        dy = max(0.0, abs(v['y'] - p['y']) - p['sy'] / 2.0)
        g = math.hypot(dx, dy) - 0.175
        if g < worst[0]:
            worst = (g, 'via (%.4f,%.4f) to pad %s-%s (%s)' % (v['x'], v['y'], p['ref'], p['pad'], p.get('net')))
chk(worst[0] >= 0.09 - 1e-6, 'no via-in-pad: new via land >= 0.09 from every SMD pad',
    'closest %.4f mm -- %s' % worst)

o = INP0['outline']
m = min(min(v['x'] - o['x0'], o['x1'] - v['x'], v['y'] - o['y0'], o['y1'] - v['y']) - 0.175 for v in P['vias'])
chk(m >= 0.80 - 1e-6, 'every new via land >= 0.80 mm inside the outline', 'least %.4f mm' % m)

chk(min(t['width'] for t in P['tracks']) >= 0.0762 - 1e-9,
    'every new track >= the global 3 mil Width minimum', 'narrowest %.4f' % min(t['width'] for t in P['tracks']))
w = INP0['nets'][NET]['width']
under = [t for t in P['tracks'] if t['width'] < (w['bottom_min'] if t['layer'] == 'Bottom' else w['top_min']) - 1e-9]
chk(not under, 'every new track meets Width_PWR_VCC3V3 AS IT STANDS TODAY', '%d below rule' % len(under))


def seg_overlap(a, b):
    if a['layer'] != b['layer']:
        return 0.0
    ax, ay, bx, by = a['x1'], a['y1'], a['x2'], a['y2']
    cx, cy, ex, ey = b['x1'], b['y1'], b['x2'], b['y2']
    ux, uy = bx - ax, by - ay
    L = math.hypot(ux, uy)
    if L < 1e-9:
        return 0.0
    ux, uy = ux / L, uy / L
    for px, py in ((cx, cy), (ex, ey)):
        if abs((px - ax) * uy - (py - ay) * ux) > 1e-4:
            return 0.0
    t1 = (cx - ax) * ux + (cy - ay) * uy
    t2 = (ex - ax) * ux + (ey - ay) * uy
    lo, hi = max(0.0, min(t1, t2)), min(L, max(t1, t2))
    return max(0.0, hi - lo)


ov = []
for a, b in itertools.combinations(allt, 2):
    L = seg_overlap(a, b)
    if L > 1e-4:
        ov.append((L, a, b))
chk(not ov, 'no collinear overlapping (doubled) VCC3V3 copper',
    '%d pair(s), %.4f mm' % (len(ov), sum(x[0] for x in ov)))
for L, a, b in ov[:6]:
    print('   OVERLAP %.4f mm %s (%.3f,%.3f)-(%.3f,%.3f) vs (%.3f,%.3f)-(%.3f,%.3f)'
          % (L, a['layer'], a['x1'], a['y1'], a['x2'], a['y2'], b['x1'], b['y1'], b['x2'], b['y2']))

TOL = 0.0015
ends = collections.Counter()
for t in allt:
    ends[(t['layer'], round(t['x1'], 4), round(t['y1'], 4))] += 1
    ends[(t['layer'], round(t['x2'], 4), round(t['y2'], 4))] += 1
mid = []
for (lay, x, y), c in ends.items():
    for t in allt:
        if t['layer'] != lay:
            continue
        if (abs(t['x1'] - x) <= TOL and abs(t['y1'] - y) <= TOL) or (abs(t['x2'] - x) <= TOL and abs(t['y2'] - y) <= TOL):
            continue
        ux, uy = t['x2'] - t['x1'], t['y2'] - t['y1']
        L = math.hypot(ux, uy)
        if L < 1e-9:
            continue
        s = ((x - t['x1']) * ux + (y - t['y1']) * uy) / L
        if s <= TOL or s >= L - TOL:
            continue
        if abs((x - t['x1']) * uy / L - (y - t['y1']) * ux / L) <= TOL:
            mid.append(((lay, x, y), t))
chk(not mid, 'no track ends on the MIDDLE of another track', '%d' % len(mid))
for k, t in mid[:6]:
    print('   MIDSPAN %s at (%.4f,%.4f) on (%.3f,%.3f)-(%.3f,%.3f)' % (k[0], k[1], k[2], t['x1'], t['y1'], t['x2'], t['y2']))


def inpad(x, y, p):
    return abs(x - p['x']) <= p['sx'] / 2.0 + 1e-9 and abs(y - p['y']) <= p['sy'] / 2.0 + 1e-9


dang = []
for (lay, x, y), c in ends.items():
    if c > 1:
        continue
    if any(abs(x - v['x']) <= TOL and abs(y - v['y']) <= TOL for v in allv):
        continue
    if any(inpad(x, y, p) for p in own + ownth):
        continue
    dang.append((lay, x, y))
chk(not dang, 'no dangling VCC3V3 track end (NetAntennae is ENABLED)', '%d' % len(dang))
for x in dang[:6]:
    print('   DANGLING %s (%.4f,%.4f)' % x)

par = {}


def find(a):
    while par.get(a, a) != a:
        par[a] = par[par[a]]
        a = par[a]
    return a


def uni(a, b):
    par.setdefault(a, a)
    par.setdefault(b, b)
    ra, rb = find(a), find(b)
    if ra != rb:
        par[ra] = rb


for t in allt:
    uni((t['layer'], round(t['x1'], 4), round(t['y1'], 4)), (t['layer'], round(t['x2'], 4), round(t['y2'], 4)))
for p in own:
    key = ('PAD', p['ref'] + '-' + str(p['pad']))
    par.setdefault(key, key)
    for t in allt:
        if t['layer'] != p['layer']:
            continue
        for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            if inpad(x, y, p):
                uni(key, (t['layer'], round(x, 4), round(y, 4)))
for v in allv:
    key = ('VIA', round(v['x'], 4), round(v['y'], 4))
    par.setdefault(key, key)
    for t in allt:
        for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            if abs(x - v['x']) <= TOL and abs(y - v['y']) <= TOL:
                uni(key, (t['layer'], round(x, 4), round(y, 4)))
grp = collections.defaultdict(list)
for k in list(par):
    grp[find(k)].append(k)
floaters = [g for g in grp.values() if not any(k[0] == 'VIA' for k in g) and not any(k[0] == 'PAD' for k in g)]
nopad = [g for g in grp.values() if not any(k[0] == 'PAD' for k in g)]
chk(not floaters, 'no VCC3V3 copper island with neither a pad nor a via', '%d' % len(floaters))
chk(True, 'islands of kept+new copper', '%d; %d hold a via but no pad (plane stitches)' % (len(grp), len(nopad)))

untied = []
for p in own:
    key = ('PAD', p['ref'] + '-' + str(p['pad']))
    g = grp[find(key)] if key in par else []
    if not any(k[0] == 'VIA' for k in g):
        untied.append(key[1])
chk(not untied, 'every VCC3V3 SMD pad island holds a via', '%d untied: %s' % (len(untied), untied[:8]))


def isl(name):
    k = ('PAD', name)
    return find(k) if k in par else None


chk(isl('L1-2') is not None and isl('L1-2') == isl('C80-2') == isl('U5-4'),
    'SC189 output loop L1-2 + C80-2 + U5-4 in ONE island', 'block_place.loop_joins requirement')

# how many barrels does each pad island hold?
hist = collections.Counter()
worstshare = []
for g in grp.values():
    pd = [k[1] for k in g if k[0] == 'PAD']
    vi = [k for k in g if k[0] == 'VIA']
    if not pd:
        continue
    hist[len(vi)] += 1
    worstshare.append((len(pd), len(vi), sorted(pd)))
worstshare.sort(reverse=True)
chk(True, 'barrels per pad island (histogram vias->islands)', dict(sorted(hist.items())))
chk(True, 'most-shared barrel', '%d pads on %d via(s): %s' % (worstshare[0][0], worstshare[0][1], ','.join(worstshare[0][2])))

print('\n%d of %d checks pass' % (len(ok), len(ok) + len(bad)))
for l in ok:
    print('  ok   ' + str(l))
for l in bad:
    print('  FAIL ' + str(l))
print('\n  pad islands with the most pads per barrel:')
for n, v, pd in worstshare[:6]:
    print('     %2d pads / %d via(s)  %s' % (n, v, ','.join(pd)))
sys.exit(1 if bad else 0)
