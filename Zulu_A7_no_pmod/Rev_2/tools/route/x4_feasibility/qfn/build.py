"""Build a QFN-U2 + S2B-X4 variant of the released no-PMOD Rev_2 board model (read-only inputs, scratch outputs).

python build.py [YC] [CX]   -> model_qfn.json, comps_qfn.json, build_report.json in this folder
"""
import copy
import json
import math
import os
import sys
from collections import defaultdict

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0, TOOLS)
import route_conn as C   # noqa
import body_check as BC  # noqa
import prune_stubs as PS  # noqa

OUT = os.environ.get('QFN_OUT', os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get('QFN_BASE', TOOLS + '/route/bodies/base.json')
COMPS = os.environ.get('QFN_COMPS', TOOLS + '/route/bodies/comps.json')
os.makedirs(OUT, exist_ok=True)
M0 = json.load(open(BASE))
D0 = json.load(open(COMPS))

YC = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
XC = float(sys.argv[2]) if len(sys.argv) > 2 else 31.475
CX = float(sys.argv[3]) if len(sys.argv) > 3 else 30.48     # S2B centre x
EP = float(sys.argv[4]) if len(sys.argv) > 4 else 4.20        # FTDI package EP is 4.35; validated PCB land is 4.20
TAG = '%s_%s_%s_%s' % (YC, XC, CX, EP)
CY = 4.9                                   # MP pads end 0.30 mm from y=0
U10_DX, U10_DY = 2.50, 1.60               # clear U3 pins; U10.8 lands on an existing VCC3V3 stack
CLR = 0.09 + 0.02                          # Clearance rule + router slack, for ripping conflicting copper

M = copy.deepcopy(M0)
D = copy.deepcopy(D0)

# ---- U2: LQFP-64 -> QFN-64 9x9 (FTDI DS_FT2232H p57; Asar validated land pattern) ----
old_u2 = [p for p in M['pads'] if p['ref'] == 'U2']
new_u2 = []
for p in old_u2:
    n = int(p['pad'])
    k = (n - 1) % 16
    off = -3.75 + 0.5 * k                     # along-side offset, same pitch and count as the LQFP
    side = (n - 1) // 16                      # 0 west (top->bottom), 1 south (l->r), 2 east (b->t), 3 north (r->l)
    if side == 0:
        x, y, w, h = XC - 4.425, YC - off, 0.75, 0.28
    elif side == 1:
        x, y, w, h = XC + off, YC - 4.425, 0.28, 0.75
    elif side == 2:
        x, y, w, h = XC + 4.425, YC + off, 0.75, 0.28
    else:
        x, y, w, h = XC - off, YC + 4.425, 0.28, 0.75
    q = dict(p, x=round(x, 4), y=round(y, 4), w=w, h=h)
    new_u2.append(q)
# check numbering is consistent with the LQFP (same side and same along-side order)
for p, q in zip(old_u2, new_u2):
    dx, dy = p['x'] - 31.475, p['y'] - 13.6000
    ex, ey = q['x'] - XC, q['y'] - YC
    assert (abs(dx) > abs(dy)) == (abs(ex) > abs(ey)) and abs((dy if abs(dx) > abs(dy) else dx) - (ey if abs(ex) > abs(ey) else ex)) < 0.01, (p, q)
ep = {'ref': 'U2', 'pad': 'EP', 'net': 'GND', 'x': XC, 'y': YC, 'shape': 'rect', 'w': 4.20, 'h': 4.20,
      'layers': ['Top Layer'], 'drill': 0.0, 'plated': False}
if EP:
    ep['w'] = ep['h'] = EP
    new_u2.append(ep)

# ---- X4: B2B-PH-SM4-TB -> S2B-PH-SM4-TB, mating face toward y=0 ----
old_x4 = [p for p in M['pads'] if p['ref'] == 'X4']
net_of = {p['pad']: p['net'] for p in old_x4}
def place(lx, ly):
    return round(CX + lx, 4), round(CY - ly, 4)
new_x4 = []
for pad, lx, ly, w, h in (('1', -1, -2.85, 1.0, 3.5), ('2', 1, -2.85, 1.0, 3.5),
                          ('MP1', -3.35, 2.9, 1.5, 3.4), ('MP2', 3.35, 2.9, 1.5, 3.4)):
    x, y = place(lx, ly)
    new_x4.append({'ref': 'X4', 'pad': pad, 'net': net_of.get(pad, ''), 'x': x, 'y': y, 'shape': 'rect', 'w': w, 'h': h,
                   'layers': ['Top Layer'], 'drill': 0.0, 'plated': False})

old_u10 = [p for p in M['pads'] if p['ref'] == 'U10']
new_u10 = [dict(p, x=round(p['x'] + U10_DX, 4), y=round(p['y'] + U10_DY, 4)) for p in old_u10]

M['pads'] = [p for p in M['pads'] if p['ref'] not in ('U2', 'X4', 'U10')] + new_u2 + new_x4 + new_u10
newpads = new_u2 + new_x4

# ---- rip ----
u2nets = {p['net'] for p in old_u2 if p['net']}
x4nets = {p['net'] for p in old_x4 if p['net']}
u10nets = {p['net'] for p in old_u10 if p['net']}
U2BOX = (24.4, 6.4, 38.6, 20.8)       # old LQFP land ring + 0.6 mm
X4BOX = (25.0, 0.0, 35.6, 10.0)       # old X4 + new S2B area
U10BOX = (17.6, 16.8, 24.2, 20.5)      # old MSOP lands and their local fan-out
def inbox(b, x, y):
    return b[0] <= x <= b[2] and b[1] <= y <= b[3]
def tin(b, t):
    return inbox(b, t['x1'], t['y1']) or inbox(b, t['x2'], t['y2'])

rip_t, rip_v, why = [], [], defaultdict(int)
keep_t, keep_v = [], []
for t in M['tracks']:
    r = None
    if t['layer'] == 'Top Layer':
        if t['net'] in u2nets and tin(U2BOX, t):
            r = 'u2-fanout'
        elif t['net'] in x4nets and tin(X4BOX, t):
            r = 'x4-fanout'
        else:
            s = (t['x1'], t['y1'], t['x2'], t['y2'])
            for p in newpads:
                if p['net'] != t['net'] or not p['net']:
                    if C.pad_seg(p, s) - t['w'] / 2 < CLR:
                        r = 'pad-conflict'
                        break
    elif t['layer'] == 'Bottom Layer':
        if t['net'] in u10nets and tin(U10BOX, t):
            r = 'u10-fanout'
        else:
            s = (t['x1'], t['y1'], t['x2'], t['y2'])
            for p in new_u10:
                if p['net'] != t['net'] or not p['net']:
                    if C.pad_seg(p, s) - t['w'] / 2 < CLR:
                        r = 'u10-pad-conflict'
                        break
    if r:
        rip_t.append(t); why[('t', r)] += 1
    else:
        keep_t.append(t)
for v in M['vias']:
    r = None
    if 'Top Layer' in v['span']:
        if v['net'] in u2nets and inbox(U2BOX, v['x'], v['y']) and v['net'] not in ('GND', 'VCC3V3'):
            r = 'u2-via'
        else:
            for p in newpads:
                if p['net'] != v['net'] or not p['net']:
                    if C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < CLR:
                        r = 'pad-conflict'
                        break
    if (r is None) and ('Bottom Layer' in v['span']):
        for p in new_u10:
            if p['net'] != v['net'] or not p['net']:
                if C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < CLR:
                    r = 'u10-pad-conflict'
                    break
    if r:
        rip_v.append(v); why[('v', r)] += 1
    else:
        keep_v.append(v)
conflicting_stacks = {(v['net'], round(v['x'], 4), round(v['y'], 4)) for v in rip_v}
still_keep_v = []
for v in keep_v:
    if (v['net'], round(v['x'], 4), round(v['y'], 4)) in conflicting_stacks:
        rip_v.append(v)
        why[('v', 'stack-mate')] += 1
    else:
        still_keep_v.append(v)
keep_v = still_keep_v
M['tracks'], M['vias'] = keep_t, keep_v
# Preserve non-conflicting routed tails so the QFN reconnects locally. A final
# composed-plan prune removes anything still dead after the replacement route.
do_prune = os.environ.get('QFN_PRUNE') == '1'
if do_prune:
    dt, dv, nt, nv = PS.analyse(M)
    M['tracks'] = [{k: v for k, v in t.items() if k != 'trimmed'} for t in nt]
    M['vias'] = nv
else:
    dt, dv = [], []

ep_vias = []
if EP:
    for dx in (-1.0, 0.0, 1.0):
        for dy in (-1.0, 0.0, 1.0):
            ep_vias.append({
                'net': 'GND',
                'x': round(XC + dx, 4),
                'y': round(YC + dy, 4),
                'size': 0.30,
                'hole': 0.15,
                'span': ['Top Layer', 'L2-GND'],
            })
    M['vias'] += ep_vias

ground_pad_vias = []
for p in newpads:
    if p['net'] != 'GND' or p['pad'] == 'EP':
        continue
    ground_pad_vias.append({
        'net': 'GND',
        'x': round(p['x'], 4),
        'y': round(p['y'], 4),
        'size': 0.30,
        'hole': 0.15,
        'span': ['Top Layer', 'L2-GND'],
    })
M['vias'] += ground_pad_vias

def L(ts):
    return sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts)

by_net = defaultdict(lambda: [0.0, 0])
for t in rip_t + [t for t in dt]:
    by_net[t['net']][0] += math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
for v in rip_v + dv:
    by_net[v['net']][1] += 1
# trimmed tracks: count the trimmed-away length
orig_len = L(keep_t)
pruned_len = orig_len - L(M['tracks'])

oc = C.open_count(C.islands(M))
rep = {'TAG': TAG, 'BASE': BASE, 'COMPS': COMPS, 'prune_enabled': do_prune,
       'XC': XC, 'EP': EP, 'YC': YC, 'CX': CX, 'CY': CY,
       'U10_DX': U10_DX, 'U10_DY': U10_DY,
       'ep_ground_vias': len(ep_vias),
       'ground_pad_vias': len(ground_pad_vias),
       'ripped_tracks': len(rip_t), 'ripped_vias': len(rip_v), 'ripped_len_mm': round(L(rip_t), 2),
       'pruned_tracks': len(dt), 'pruned_vias': len(dv), 'pruned_len_mm': round(pruned_len, 2),
       'why': {'%s:%s' % k: n for k, n in why.items()},
       'per_net': {n: [round(a, 2), b] for n, (a, b) in sorted(by_net.items())},
       'open': oc, 'open_total': sum(oc.values())}

# ---- bodies ----
for c in D['comps']:
    if c['ref'] == 'U2':
        c['pattern'] = 'FT2232HQ-QFN64'
    if c['ref'] == 'X4':
        c['pattern'] = 'JST-S2B-PH-SM4-TB'
        c['rot'] = 0.0
BC.BODY['FT2232HQ-QFN64'] = (9.0, 9.0, 9.1, 9.1)
pe = (CX - 4.1, CY - 4.6, CX + 4.1, CY + 4.6)
bd = (CX - 3.95, CY - 4.4, CX + 3.95, CY + 3.2)          # KiCad F.Fab outline bbox, turned 180
D['mech']['X4'] = {'side': 'Top', 'pad_ext': list(pe), 'body': list(bd),
                   'off': [bd[0] - pe[0], bd[1] - pe[1], bd[2] - pe[2], bd[3] - pe[3]]}
parts = BC.build(M, D)
bc = BC.check(parts, {'U2', 'X4'}, 0.10)
fast = os.environ.get('QFN_FAST') == '1'
bc_all = [] if fast else BC.check(parts, None, 0.10)
base_all = [] if fast else BC.check(BC.build(M0, D0), None, 0.10)
rep['body_check_U2_X4'] = bc
rep['body_check_all_new'] = None if fast else len(bc_all)
rep['body_check_all_base'] = None if fast else len(base_all)
rep['body_check_all_new_list'] = bc_all
rep['body_check_all_base_list'] = base_all
rep['U2_body'] = parts['Top']['U2']['body']
rep['X4_body'] = parts['Top']['X4']['body']
rep['U10_body'] = parts['Bottom']['U10']['body']

# ---- pad-to-pad clearance of the new pads vs every other part's pads on Top ----
def pbox(p):
    return (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
pp = []
for q in newpads:
    for p in M['pads']:
        if p['ref'] == q['ref']:
            continue
        if p['layers'] and 'Top Layer' not in p['layers']:
            continue
        if not p['layers'] and not p['drill']:
            continue
        if C.pad_round(p) or p['shape'] == 'circle':
            g = C.pad_point(q, p['x'], p['y']) - min(p['w'], p['h']) / 2
        else:
            g = BC.gap(pbox(q), pbox(p))
        if g < 0.6:
            pp.append((q['ref'] + '-' + q['pad'], p['ref'] + '-' + p['pad'], round(g, 3)))
pp.sort(key=lambda r: r[2])
rep['pad_pad_nearest'] = pp[:12]
# edge clearance of new copper
rep['edge_min'] = round(min(min(p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, 60.96 - p['x'] - p['w'] / 2,
                                25.4 - p['y'] - p['h'] / 2) for p in newpads), 3)
# within-part pad gaps, S2B signal pad to U2 south pads, U2 north pads to X1
json.dump(M, open(os.path.join(OUT, 'model_%s.json' % TAG), 'w'))
json.dump(D, open(os.path.join(OUT, 'comps_%s.json' % TAG), 'w'), indent=0)
json.dump({'u2': new_u2, 'x4': new_x4, 'u10': new_u10},
          open(os.path.join(OUT, 'newpads_%s.json' % TAG), 'w'), indent=0)
json.dump(rep, open(os.path.join(OUT, 'build_report_%s.json' % TAG), 'w'), indent=1)
for k in ('YC', 'ripped_tracks', 'ripped_vias', 'ripped_len_mm', 'pruned_tracks', 'pruned_vias', 'pruned_len_mm',
          'why', 'open_total', 'open', 'body_check_U2_X4', 'body_check_all_new', 'body_check_all_base', 'U2_body',
          'X4_body', 'pad_pad_nearest', 'edge_min'):
    print(k, rep[k])
print('per_net', rep['per_net'])
