"""Build an FT2232H-56Q U2 + S2B-PH-SM4-TB X4 feasibility model.

python build.py [YC] [XC] [CX] -> model_*.json, comps_*.json, newpads_*.json,
                                  and build_report_*.json in this folder
"""
import copy
import json
import math
import os
import sys
from collections import defaultdict

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
sys.path.insert(0, TOOLS)
import body_check as BC  # noqa: E402
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
M0 = json.load(open(TOOLS + '/route/bodies/base.json'))
D0 = json.load(open(TOOLS + '/route/bodies/comps.json'))

YC = float(sys.argv[1]) if len(sys.argv) > 1 else 14.0
XC = float(sys.argv[2]) if len(sys.argv) > 2 else 31.475
CX = float(sys.argv[3]) if len(sys.argv) > 3 else 30.48
CY = 4.9
TAG = '%s_%s_%s' % (YC, XC, CX)
CLR = 0.09 + 0.02

M = copy.deepcopy(M0)
D = copy.deepcopy(D0)


def lqfp64_functions():
    f = {
        1: 'GND', 2: 'OSCI', 3: 'OSCO', 4: 'VPHY', 5: 'GND', 6: 'REF', 7: 'DM', 8: 'DP',
        9: 'VPLL', 10: 'AGND', 11: 'GND', 12: 'VCORE', 13: 'TEST', 14: 'RESET#', 15: 'GND',
        20: 'VCCIO', 25: 'GND', 31: 'VCCIO', 35: 'GND', 36: 'SUSPEND#', 37: 'VCORE',
        42: 'VCCIO', 47: 'GND', 49: 'VREGOUT', 50: 'VREGIN', 51: 'GND', 56: 'VCCIO',
        60: 'PWREN#', 61: 'EEDATA', 62: 'EECLK', 63: 'EECS', 64: 'VCORE',
    }
    for i, n in enumerate(range(16, 20)):
        f[n] = 'ADBUS%d' % i
    for i, n in enumerate(range(21, 25), 4):
        f[n] = 'ADBUS%d' % i
    for i, n in enumerate(range(26, 31)):
        f[n] = 'ACBUS%d' % i
    for i, n in enumerate(range(32, 35), 5):
        f[n] = 'ACBUS%d' % i
    for i, n in enumerate(range(38, 42)):
        f[n] = 'BDBUS%d' % i
    for i, n in enumerate(range(43, 47), 4):
        f[n] = 'BDBUS%d' % i
    f[48] = 'BCBUS0'
    for i, n in enumerate(range(52, 56), 1):
        f[n] = 'BCBUS%d' % i
    for i, n in enumerate(range(57, 60), 5):
        f[n] = 'BCBUS%d' % i
    return f


def vqfn56_functions():
    f = {
        1: 'EECS', 2: 'VCORE', 3: 'OSCI', 4: 'OSCO', 5: 'VPHY', 6: 'REF', 7: 'DM', 8: 'DP',
        9: 'VPLL', 10: 'TEST', 11: 'RESET#', 16: 'VCCIO', 21: 'GND', 30: 'SUSPEND#',
        31: 'VCORE', 36: 'VCCIO', 41: 'GND', 42: 'BCBUS0', 43: 'VREGOUT',
        44: 'VREGIN', 45: 'GND', 50: 'VCCIO', 54: 'PWREN#', 55: 'EEDATA', 56: 'EECLK',
    }
    for i, n in enumerate((12, 13, 14, 15, 17, 18, 19, 20)):
        f[n] = 'ADBUS%d' % i
    for i, n in enumerate(range(22, 30)):
        f[n] = 'ACBUS%d' % i
    for i, n in enumerate((32, 33, 34, 35, 37, 38, 39, 40)):
        f[n] = 'BDBUS%d' % i
    for i, n in enumerate(range(46, 50), 1):
        f[n] = 'BCBUS%d' % i
    for i, n in enumerate(range(51, 54), 5):
        f[n] = 'BCBUS%d' % i
    return f


# ---- U2: FT2232HL LQFP-64 -> FT2232H-56Q 8 x 8 mm VQFN-56 ----
old_u2 = [p for p in M['pads'] if p['ref'] == 'U2']
old_fn = lqfp64_functions()
new_fn = vqfn56_functions()
net_by_fn = {}
for p in old_u2:
    fn = old_fn[int(p['pad'])]
    net = p['net']
    if fn in net_by_fn:
        assert net_by_fn[fn] == net, (fn, net_by_fn[fn], net)
    else:
        net_by_fn[fn] = net
net_by_fn['GND'] = 'GND'

new_u2 = []
template = old_u2[0]
for n in range(1, 57):
    k = (n - 1) % 14
    off = 3.25 - 0.5 * k
    side = (n - 1) // 14
    if side == 0:
        x, y, w, h = XC - 3.9375, YC + off, 0.875, 0.25
    elif side == 1:
        x, y, w, h = XC - off, YC - 3.9375, 0.25, 0.875
    elif side == 2:
        x, y, w, h = XC + 3.9375, YC - off, 0.875, 0.25
    else:
        x, y, w, h = XC + off, YC + 3.9375, 0.25, 0.875
    fn = new_fn[n]
    new_u2.append(dict(
        template,
        pad=str(n),
        net=net_by_fn.get(fn, ''),
        x=round(x, 4),
        y=round(y, 4),
        w=w,
        h=h,
    ))
new_u2.append({
    'ref': 'U2', 'pad': '57', 'net': 'GND', 'x': XC, 'y': YC, 'shape': 'rect',
    'w': 5.9, 'h': 5.9, 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False,
})

used_old = {old_fn[int(p['pad'])]: p['net'] for p in old_u2 if p['net']}
used_new = {new_fn[int(p['pad'])]: p['net'] for p in new_u2 if p['pad'] != '57' and p['net']}
for fn, net in used_old.items():
    if fn == 'AGND':
        continue
    assert used_new.get(fn) == net, (fn, net, used_new.get(fn))

# ---- X4: JST S2B-PH-SM4-TB, mating face toward the south board edge ----
old_x4 = [p for p in M['pads'] if p['ref'] == 'X4']
net_of = {p['pad']: p['net'] for p in old_x4}


def rot(lx, ly):
    return round(CX - lx, 4), round(CY - ly, 4)


new_x4 = []
for pad, lx, ly, w, h in (
    ('1', -1, -2.85, 1.0, 3.5),
    ('2', 1, -2.85, 1.0, 3.5),
    ('MP1', -3.35, 2.9, 1.5, 3.4),
    ('MP2', 3.35, 2.9, 1.5, 3.4),
):
    x, y = rot(lx, ly)
    new_x4.append({
        'ref': 'X4', 'pad': pad, 'net': net_of[pad], 'x': x, 'y': y, 'shape': 'rect',
        'w': w, 'h': h, 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False,
    })

M['pads'] = [p for p in M['pads'] if p['ref'] not in ('U2', 'X4')] + new_u2 + new_x4
newpads = new_u2 + new_x4

# ---- rip only copper invalidated by the replacement footprints ----
u2nets = {p['net'] for p in old_u2 if p['net']}
x4nets = {p['net'] for p in old_x4 if p['net']}
U2BOX = (24.4, 6.4, 38.6, 20.8)
X4BOX = (25.0, 0.0, 35.6, 10.0)


def inbox(b, x, y):
    return b[0] <= x <= b[2] and b[1] <= y <= b[3]


def tin(b, t):
    return inbox(b, t['x1'], t['y1']) or inbox(b, t['x2'], t['y2'])


rip_t, rip_v, why = [], [], defaultdict(int)
keep_t, keep_v = [], []
for t in M['tracks']:
    reason = None
    if t['layer'] == 'Top Layer':
        if t['net'] in u2nets and tin(U2BOX, t):
            reason = 'u2-fanout'
        elif t['net'] in x4nets and tin(X4BOX, t):
            reason = 'x4-fanout'
        else:
            s = (t['x1'], t['y1'], t['x2'], t['y2'])
            for p in newpads:
                if p['net'] != t['net'] or not p['net']:
                    if C.pad_seg(p, s) - t['w'] / 2 < CLR:
                        reason = 'pad-conflict'
                        break
    if reason:
        rip_t.append(t)
        why[('t', reason)] += 1
    else:
        keep_t.append(t)
for v in M['vias']:
    reason = None
    if 'Top Layer' in v['span']:
        if v['net'] in u2nets and inbox(U2BOX, v['x'], v['y']) and v['net'] not in ('GND', 'VCC3V3'):
            reason = 'u2-via'
        else:
            for p in newpads:
                if p['net'] != v['net'] or not p['net']:
                    if C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < CLR:
                        reason = 'pad-conflict'
                        break
    if reason:
        rip_v.append(v)
        why[('v', reason)] += 1
    else:
        keep_v.append(v)
M['tracks'], M['vias'] = keep_t, keep_v
dt, dv, nt, nv = PS.analyse(M)
M['tracks'] = [{k: v for k, v in t.items() if k != 'trimmed'} for t in nt]
M['vias'] = nv


def length(tracks):
    return sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in tracks)


by_net = defaultdict(lambda: [0.0, 0])
for t in rip_t + list(dt):
    by_net[t['net']][0] += math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
for v in rip_v + dv:
    by_net[v['net']][1] += 1
orig_len = length(keep_t)
pruned_len = orig_len - length(M['tracks'])
opens = C.open_count(C.islands(M))

rep = {
    'TAG': TAG, 'XC': XC, 'YC': YC, 'CX': CX, 'CY': CY,
    'ripped_tracks': len(rip_t), 'ripped_vias': len(rip_v), 'ripped_len_mm': round(length(rip_t), 2),
    'pruned_tracks': len(dt), 'pruned_vias': len(dv), 'pruned_len_mm': round(pruned_len, 2),
    'why': {'%s:%s' % k: n for k, n in why.items()},
    'per_net': {n: [round(a, 2), b] for n, (a, b) in sorted(by_net.items())},
    'open': opens, 'open_total': sum(opens.values()),
    'pin_nets': {p['pad']: p['net'] for p in new_u2},
}

# ---- body and pad clearance ----
for c in D['comps']:
    if c['ref'] == 'U2':
        c['pattern'] = 'FT2232H-56Q'
    elif c['ref'] == 'X4':
        c['pattern'] = 'JST-S2B-PH-SM4-TB'
        c['rot'] = 180.0
BC.BODY['FT2232H-56Q'] = (8.0, 8.0, 8.1, 8.1)
pe = (CX - 4.1, CY - 4.6, CX + 4.1, CY + 4.6)
bd = (CX - 3.95, CY - 4.4, CX + 3.95, CY + 3.2)
D['mech']['X4'] = {
    'side': 'Top', 'pad_ext': list(pe), 'body': list(bd),
    'off': [bd[0] - pe[0], bd[1] - pe[1], bd[2] - pe[2], bd[3] - pe[3]],
}
parts = BC.build(M, D)
body_u2_x4 = BC.check(parts, {'U2', 'X4'}, 0.10)
body_all = BC.check(parts, None, 0.10)
body_base = BC.check(BC.build(M0, D0), None, 0.10)
rep['body_check_U2_X4'] = body_u2_x4
rep['body_check_all_new'] = len(body_all)
rep['body_check_all_base'] = len(body_base)
rep['body_check_all_new_list'] = body_all
rep['body_check_all_base_list'] = body_base
rep['U2_body'] = parts['Top']['U2']['body']
rep['X4_body'] = parts['Top']['X4']['body']


def pbox(p):
    return (
        p['x'] - p['w'] / 2, p['y'] - p['h'] / 2,
        p['x'] + p['w'] / 2, p['y'] + p['h'] / 2,
    )


pad_gaps = []
for q in newpads:
    for p in M['pads']:
        if p['ref'] == q['ref']:
            continue
        if p['layers'] and 'Top Layer' not in p['layers']:
            continue
        if not p['layers'] and not p['drill']:
            continue
        if C.pad_round(p) or p['shape'] == 'circle':
            gap = C.pad_point(q, p['x'], p['y']) - min(p['w'], p['h']) / 2
        else:
            gap = BC.gap(pbox(q), pbox(p))
        if gap < 0.6:
            pad_gaps.append((q['ref'] + '-' + q['pad'], p['ref'] + '-' + p['pad'], round(gap, 3)))
pad_gaps.sort(key=lambda r: r[2])
rep['pad_pad_nearest'] = pad_gaps[:20]
rep['edge_min'] = round(min(
    min(
        p['x'] - p['w'] / 2,
        p['y'] - p['h'] / 2,
        60.96 - p['x'] - p['w'] / 2,
        25.4 - p['y'] - p['h'] / 2,
    )
    for p in newpads
), 3)

json.dump(M, open(os.path.join(OUT, 'model_%s.json' % TAG), 'w'))
json.dump(D, open(os.path.join(OUT, 'comps_%s.json' % TAG), 'w'), indent=0)
json.dump({'u2': new_u2, 'x4': new_x4}, open(os.path.join(OUT, 'newpads_%s.json' % TAG), 'w'), indent=0)
json.dump(rep, open(os.path.join(OUT, 'build_report_%s.json' % TAG), 'w'), indent=1)
for key in (
    'YC', 'XC', 'CX', 'ripped_tracks', 'ripped_vias', 'ripped_len_mm', 'pruned_tracks',
    'pruned_vias', 'pruned_len_mm', 'why', 'open_total', 'open', 'body_check_U2_X4',
    'body_check_all_new', 'body_check_all_base', 'U2_body', 'X4_body',
    'pad_pad_nearest', 'edge_min',
):
    print(key, rep[key])
print('per_net', rep['per_net'])
