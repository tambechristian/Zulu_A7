"""Build an original-FT2232HL + south-edge-tab S2B-PH-SM4-TB feasibility model.

The rectangular router model remains the original board because all routed X4
signal copper stays north of y=0. The two mechanical pads sit on the tab.
"""
import copy
import json
import math
import os
import sys
from collections import defaultdict

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0, TOOLS)
import body_check as BC  # noqa: E402
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
M0 = json.load(open(TOOLS + '/route/bodies/base.json'))
D0 = json.load(open(TOOLS + '/route/bodies/comps.json'))

CX = float(sys.argv[1]) if len(sys.argv) > 1 else 30.48
CY = float(sys.argv[2]) if len(sys.argv) > 2 else 2.20
TAB_NECK = float(sys.argv[3]) if len(sys.argv) > 3 else 9.60
TAB_OUTER = 8.80
TAB_DEPTH = 4.90 - CY
CLR = 0.11
TAG = '%s_%s_%s' % (CX, CY, TAB_NECK)

M = copy.deepcopy(M0)
D = copy.deepcopy(D0)

# JST S2B-PH-SM4-TB, rotated 180 degrees so the cable exits south.
old_x4 = [p for p in M['pads'] if p['ref'] == 'X4']
net_of = {p['pad']: p['net'] for p in old_x4}


def rot(lx, ly):
    return round(CX - lx, 4), round(CY - ly, 4)


new_x4 = []
for pad, lx, ly, w, h in (
    ('1', -1.0, -2.85, 1.0, 3.5),
    ('2', 1.0, -2.85, 1.0, 3.5),
    ('MP1', -3.35, 2.90, 1.5, 3.4),
    ('MP2', 3.35, 2.90, 1.5, 3.4),
):
    x, y = rot(lx, ly)
    new_x4.append({
        'ref': 'X4', 'pad': pad, 'net': net_of[pad], 'x': x, 'y': y,
        'shape': 'rect', 'w': w, 'h': h, 'layers': ['Top Layer'],
        'drill': 0.0, 'plated': False,
    })
M['pads'] = [p for p in M['pads'] if p['ref'] != 'X4'] + new_x4
M_MOVED = copy.deepcopy(M)

# Remove only the old X4 fan-out and copper conflicting with its replacement pads.
x4nets = {p['net'] for p in old_x4 if p['net']}
X4BOX = (24.5, 0.0, 36.5, 8.0)


def inbox(box, x, y):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def tin(box, track):
    return (
        inbox(box, track['x1'], track['y1']) or
        inbox(box, track['x2'], track['y2'])
    )


rip_t, rip_v, why = [], [], defaultdict(int)
keep_t, keep_v = [], []
for t in M['tracks']:
    reason = None
    if t['layer'] == 'Top Layer':
        if t['net'] in x4nets and tin(X4BOX, t):
            reason = 'x4-fanout'
        else:
            seg = (t['x1'], t['y1'], t['x2'], t['y2'])
            for p in new_x4:
                if (p['net'] != t['net'] or not p['net']) and C.pad_seg(p, seg) - t['w'] / 2 < CLR:
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
        if v['net'] in x4nets and inbox(X4BOX, v['x'], v['y']) and v['net'] != 'GND':
            reason = 'x4-via'
        else:
            for p in new_x4:
                if (p['net'] != v['net'] or not p['net']) and C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < CLR:
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


opens = C.open_count(C.islands(M))
rep = {
    'CX': CX,
    'CY': CY,
    'tab_depth': TAB_DEPTH,
    'tab_neck_width': TAB_NECK,
    'tab_outer_width': TAB_OUTER,
    'tab_outline': [
        [round(CX - TAB_NECK / 2, 4), 0.0],
        [round(CX - TAB_OUTER / 2, 4), round(-TAB_DEPTH, 4)],
        [round(CX + TAB_OUTER / 2, 4), round(-TAB_DEPTH, 4)],
        [round(CX + TAB_NECK / 2, 4), 0.0],
    ],
    'ripped_tracks': len(rip_t),
    'ripped_vias': len(rip_v),
    'ripped_len_mm': round(length(rip_t), 2),
    'pruned_tracks': len(dt),
    'pruned_vias': len(dv),
    'why': {'%s:%s' % key: value for key, value in why.items()},
    'open': opens,
    'open_total': sum(opens.values()),
}

# Exact body model and collision checks.
for comp in D['comps']:
    if comp['ref'] == 'X4':
        comp['pattern'] = 'JST-S2B-PH-SM4-TB'
        comp['rot'] = 180.0
pad_extent = (CX - 4.1, CY - 4.6, CX + 4.1, CY + 4.6)
body = (CX - 3.95, CY - 4.4, CX + 3.95, CY + 3.2)
D['mech']['X4'] = {
    'side': 'Top',
    'pad_ext': list(pad_extent),
    'body': list(body),
    'off': [
        body[0] - pad_extent[0], body[1] - pad_extent[1],
        body[2] - pad_extent[2], body[3] - pad_extent[3],
    ],
}
parts = BC.build(M, D)
body_new = BC.check(parts, {'X4'}, 0.10)
body_base = BC.check(BC.build(M0, D0), None, 0.10)
rep['body_check_X4'] = body_new
rep['body_check_all_new'] = len(BC.check(parts, None, 0.10))
rep['body_check_all_base'] = len(body_base)
rep['X4_body'] = body


def pbox(p):
    return (
        p['x'] - p['w'] / 2, p['y'] - p['h'] / 2,
        p['x'] + p['w'] / 2, p['y'] + p['h'] / 2,
    )


pad_gaps = []
for q in new_x4:
    for p in M['pads']:
        if p['ref'] == 'X4':
            continue
        if p['layers'] and 'Top Layer' not in p['layers']:
            continue
        if not p['layers'] and not p['drill']:
            continue
        if C.pad_round(p) or p['shape'] == 'circle':
            gap = C.pad_point(q, p['x'], p['y']) - min(p['w'], p['h']) / 2
        else:
            gap = BC.gap(pbox(q), pbox(p))
        pad_gaps.append((q['pad'], p['ref'] + '-' + p['pad'], round(gap, 3)))
pad_gaps.sort(key=lambda row: row[2])
rep['pad_pad_nearest'] = pad_gaps[:12]

# The mounting pads set the limiting tab clearances by construction.
side_run = (TAB_NECK - TAB_OUTER) / 2
side_clearance = (
    TAB_OUTER / 2 +
    side_run * (TAB_DEPTH - (TAB_DEPTH - 0.3)) / TAB_DEPTH -
    4.1
)
rep['mount_pad_bottom_edge_clearance'] = 0.3
rep['mount_pad_side_clearance_near_bottom'] = round(side_clearance, 3)
rep['u2_south_pad_clearance'] = round(
    min(
        BC.gap(pbox(q), pbox(p))
        for q in new_x4 if q['pad'] in ('1', '2')
        for p in M['pads'] if p['ref'] == 'U2'
    ),
    3,
)

json.dump(M, open(os.path.join(OUT, 'model_%s.json' % TAG), 'w'))
json.dump(M_MOVED, open(os.path.join(OUT, 'base_moved_%s.json' % TAG), 'w'))
json.dump(D, open(os.path.join(OUT, 'comps_%s.json' % TAG), 'w'), indent=0)
json.dump({'x4': new_x4}, open(os.path.join(OUT, 'newpads_%s.json' % TAG), 'w'), indent=0)
json.dump({
    'moves': [],
    'remove': rip_t,
    'remove_vias': rip_v,
    'tracks': [],
    'vias': [],
}, open(os.path.join(OUT, 'rip_%s.json' % TAG), 'w'), indent=1)
json.dump(rep, open(os.path.join(OUT, 'build_report_%s.json' % TAG), 'w'), indent=1)
for key in (
    'CX', 'CY', 'tab_depth', 'tab_neck_width', 'tab_outer_width', 'tab_outline',
    'ripped_tracks', 'ripped_vias', 'ripped_len_mm', 'pruned_tracks',
    'pruned_vias', 'why', 'open_total', 'open', 'body_check_X4',
    'body_check_all_new', 'body_check_all_base', 'pad_pad_nearest',
    'mount_pad_bottom_edge_clearance', 'mount_pad_side_clearance_near_bottom',
    'u2_south_pad_clearance',
):
    print(key, rep[key])
