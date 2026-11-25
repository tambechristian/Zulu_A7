"""Shared geometry for the u2-west feasibility study (read-only on the board files)."""
import copy
import json
import math
import sys

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0, TOOLS)
import body_check as BC  # noqa: E402
import route_conn as RC  # noqa: E402

M0 = json.load(open(TOOLS + '/route/bodies/base.json'))
D0 = json.load(open(TOOLS + '/route/bodies/comps.json'))
W, H = M0['board']['w'], M0['board']['h']
CLEAR = 0.09
SDRAM = set(['A%d' % i for i in range(13)] + ['BS0', 'BS1', 'CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM',
                                           'SDRAM-CLK', 'SDRAM-CS#'] + ['D%d' % i for i in range(16)] +
            ['SDRAM-D%d' % i for i in range(16)])


def ext(ps):
    return (min(p['x'] - p['w'] / 2 for p in ps), min(p['y'] - p['h'] / 2 for p in ps),
            max(p['x'] + p['w'] / 2 for p in ps), max(p['y'] + p['h'] / 2 for p in ps))


def centre(ps):
    e = ext(ps)
    return (e[0] + e[2]) / 2, (e[1] + e[3]) / 2


def s2b_pads(cx, cy, n1='VBATT', n2='GND'):
    """JST S2B-PH-SM4-TB rotated 180 deg (mating face toward -y). local (x,y) -> board (cx-x, cy-y).
    pin1 local (-1,-2.85) -> (cx+1, cy+2.85); keep the current X4 net order (pad1 VBATT, pad2 GND)."""
    L = [('1', n1, -1.0, -2.85, 1.0, 3.5), ('2', n2, 1.0, -2.85, 1.0, 3.5),
         ('MP1', '', -3.35, 2.9, 1.5, 3.4), ('MP2', '', 3.35, 2.9, 1.5, 3.4)]
    return [{'ref': 'X4', 'pad': n, 'net': net, 'x': cx - x, 'y': cy - y, 'shape': 'rect', 'w': w, 'h': h,
             'layers': ['Top Layer'], 'drill': 0.0, 'plated': False} for n, net, x, y, w, h in L]


def s2b_mech():
    # pad extent local x +-4.1, y -4.6..+4.6 ; body x +-3.95, y -3.2..+4.4 ; rotated 180 -> body y cy-4.4..cy+3.2
    return {'side': 'Top', 'off': [0.15, 0.2, -0.15, -1.4]}


def rot_pt(x, y, cx, cy, deg):
    a = math.radians(deg)
    dx, dy = x - cx, y - cy
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)


def place(M, D, ref, nx, ny, drot=0):
    """move ref so its pad-extent centre lands on (nx, ny), rotated by drot (deg CCW) about that centre."""
    ps = [p for p in M['pads'] if p['ref'] == ref]
    cx, cy = centre(ps)
    for p in ps:
        x, y = rot_pt(p['x'], p['y'], cx, cy, drot)
        if round(drot) % 180 == 90:
            p['w'], p['h'] = p['h'], p['w']
        p['x'], p['y'] = x - cx + nx, y - cy + ny
    for c in D['comps']:
        if c['ref'] == ref:
            c['rot'] = (c['rot'] + drot) % 360


def build(placements, s2b=(30.48, 4.9)):
    """placements: {ref: (x, y, drot)}; returns modified (M, D)."""
    M = {'board': M0['board'], 'planes': M0['planes'], 'pads': copy.deepcopy(M0['pads']),
         'tracks': M0['tracks'], 'vias': M0['vias']}
    D = copy.deepcopy(D0)
    for ref, (x, y, r) in placements.items():
        place(M, D, ref, x, y, r)
    if s2b:
        M['pads'] = [p for p in M['pads'] if p['ref'] != 'X4'] + s2b_pads(*s2b)
        D['mech']['X4'] = s2b_mech()
        for c in D['comps']:
            if c['ref'] == 'X4':
                c['pattern'] = 'JST-S2B-PH-SM4-TB'
                c['rot'] = 180.0
    return M, D


def pad_gap(a, b):
    """copper gap between two pads (rect / circle approximated as rect for circles: conservative)."""
    dx = max(abs(a['x'] - b['x']) - (a['w'] + b['w']) / 2, 0)
    dy = max(abs(a['y'] - b['y']) - (a['h'] + b['h']) / 2, 0)
    if a['shape'] == 'circle' and b['shape'] == 'circle':
        return math.hypot(a['x'] - b['x'], a['y'] - b['y']) - (a['w'] + b['w']) / 2
    if a['shape'] == 'circle' or b['shape'] == 'circle':
        c, r = (a, b) if a['shape'] == 'circle' else (b, a)
        return RC.pad_point(r, c['x'], c['y']) - c['w'] / 2
    return math.hypot(dx, dy) if (dx > 0 and dy > 0) else max(dx, dy) if (dx > 0 or dy > 0) else \
        -min((a['w'] + b['w']) / 2 - abs(a['x'] - b['x']), (a['h'] + b['h']) / 2 - abs(a['y'] - b['y']))


def on_top(p):
    return p['layers'] is None or 'Top Layer' in p['layers']


def pad_checks(M, refs, min_gap=0.2, edge=0.3):
    """pad-to-pad (other parts, shared outer layer) and pad-to-edge for the given refs."""
    out = []
    mv = [p for p in M['pads'] if p['ref'] in refs]
    others = [p for p in M['pads'] if p['ref'] not in refs]
    for a in mv:
        e = (a['x'] - a['w'] / 2, a['y'] - a['h'] / 2, a['x'] + a['w'] / 2, a['y'] + a['h'] / 2)
        de = min(e[0], e[1], W - e[2], H - e[3])
        if de < edge - 1e-6:
            out.append(('edge', a['ref'], a['pad'], round(de, 3)))
        for b in others + [q for q in mv if q['ref'] != a['ref']]:
            if abs(a['x'] - b['x']) > 6 or abs(a['y'] - b['y']) > 6:
                continue
            la = set(a['layers'] or BC.STACK) & {'Top Layer', 'Bottom Layer'}
            lb = set(b['layers'] or BC.STACK) & {'Top Layer', 'Bottom Layer'}
            if not la & lb:
                continue
            g = pad_gap(a, b)
            if g < min_gap - 1e-6:
                out.append(('pad_pad', a['ref'] + '.' + a['pad'], b['ref'] + '.' + b['pad'], round(g, 3)))
    return out


def body_findings(M, D, refs, gap=0.10):
    parts = BC.build(M, D)
    return BC.check(parts, set(refs) if refs else None, gap)
