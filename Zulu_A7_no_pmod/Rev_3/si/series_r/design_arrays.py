# -*- coding: utf-8 -*-
"""Series-R plan for D0-D15 at U3 (AS4C32M16SB TSOP-II, Bottom) -- 'arrays' approach, compared with discretes.

    python si/series_r/design_arrays.py            -> design_arrays.json + design_arrays.png (this folder)

READ-ONLY on the board: reads si/series_r/board_extract.json (the saved PcbDoc, see its 'source' md5) and
writes only design_arrays.json / design_arrays.png here.  Nothing in Altium, the PcbDoc, SchDocs or PcbLib.

Steps
  1. Topology of the insertion (why the R goes OUTWARD of U3's pad toes on Bottom and its far end folds back
     through a gap between two U3 pads to the existing first via): measured, per DQ, from the extract.
  2. Gap budget along both TSOP rows: which inter-pad gaps are already used by other nets (measured).
  3. Arrays: for every way of grouping the DQs into 4- and 2-element arrays, a planarity test (a return can
     only leave around the array's ends, never between two of its elements at 0.4/0.5 mm pitch) + gap test.
  4. The discrete-0201 plan that wins, with every copper record removed/added, every moved part, and the
     rule check of plan_check.py against the whole board (clearance, sliver, hole-to-hole, width,
     connectivity, antennae; component clearance as advisory).
  5. Electrical position of each R (U3 pad centre -> R pad centre along the copper; ps from the fab-stack
     field-solve tables in si/spice/lines.json when available, else an assumed 6.6 ps/mm for Bottom 0.125 mm).
"""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
sys.path.insert(0, HERE)
import plan_check as P

OUT_JSON = HERE + '/design_arrays.json'
OUT_PNG = HERE + '/design_arrays.png'

B = P.Board()
D = B.d
U3 = {p['pad']: p for p in D['pads'] if p['ref'] == 'U3'}
ESC = D['d_escapes']
DQ_PIN = {'D0': 2, 'D1': 4, 'D2': 5, 'D3': 7, 'D4': 8, 'D5': 10, 'D6': 11, 'D7': 13,
          'D8': 42, 'D9': 44, 'D10': 45, 'D11': 47, 'D12': 48, 'D13': 50, 'D14': 51, 'D15': 53}
PAD_HALF_L = 0.59995           # U3 pad half-length along y (1.1999 / 2)
TOE_GAP = 0.21                 # U3 toe -> R pad edge: 0.10 mask web + 2 x 0.05 expansion + 0.01 margin
R_PITCH = 0.60                 # R0201 pad centre spacing (zulu_a7.PcbLib R0201)
R_PAD = 0.30
W_RET = 0.10                   # Bottom D-net minimum (Width_SDRAM BOTTOMLAYER_MINWIDTH) -- used in the 0.35 mm pad gaps
W_FEED = 0.125                 # Bottom preferred


def pin_xy(net):
    p = U3[str(DQ_PIN[net])]
    return p['x'], p['y']


def row_sign(net):
    return -1 if pin_xy(net)[1] < 12 else 1          # outward direction: south row -y, north row +y


def first_via(net):
    v = ESC[net]['first_via']
    return v['x'], v['y']


def old_stub(net):
    return [dict(layer='Bottom', net=net, x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'])
            for t in ESC[net]['bottom_stub'] if t['kind'] == 'track']


# ----------------------------------------------------------------------------- R templates
def place_R(net, A, Bp, feed, ret, ret_w=None):
    """A = pad 1 (SDRAM-Dn, U3 side), Bp = pad 2 (Dn). Bottom-side rotation from the board's own 0201s
    (R117 rot 0: pad1 -x; R114 rot 180: pad1 +x; R118 rot 270: pad1 +y; so rot 90: pad1 -y)."""
    dx, dy = A[0] - Bp[0], A[1] - Bp[1]
    if abs(dy) < 1e-6:
        rot = 0 if dx < 0 else 180
    else:
        rot = 90 if dy < 0 else 270
    cx, cy = (A[0] + Bp[0]) / 2, (A[1] + Bp[1]) / 2
    sn = 'SDRAM-' + net
    tracks = []
    for a, b in zip(feed, feed[1:]):
        tracks.append(dict(layer='Bottom', net=sn, x1=a[0], y1=a[1], x2=b[0], y2=b[1], w=W_FEED))
    for k, (a, b) in enumerate(zip(ret, ret[1:])):
        w = (ret_w[k] if ret_w else W_RET)
        tracks.append(dict(layer='Bottom', net=net, x1=a[0], y1=a[1], x2=b[0], y2=b[1], w=w))
    return dict(net=net, ref=None, x=round(cx, 4), y=round(cy, 4), rot=rot, side='Bottom',
                pads=[dict(pad='1', net=sn, x=A[0], y=A[1]), dict(pad='2', net=net, x=Bp[0], y=Bp[1])],
                tracks=tracks)


def tpl(net, kind, s, via=None, extra_in=0.2, dyoff=0.0):
    """kind HA: horizontal, pad 1 on the pin column, pad 2 toward gap side s (+-1);
            HB: horizontal, pad 2 centred on the gap, pad 1 0.6 back toward the pin;
            V : vertical, both pads on the pin column, return jogs 45 deg into the gap."""
    xp, yp = pin_xy(net)
    o = row_sign(net)
    toe = yp + o * PAD_HALF_L
    inner = yp - o * PAD_HALF_L
    g = xp + 0.4 * s
    vx, vy = via if via else first_via(net)
    yc = toe + o * (TOE_GAP + R_PAD / 2 + dyoff)
    if kind == 'HA':
        A, Bp = (xp, yc), (xp + R_PITCH * s, yc)
        feed = [(xp, yp), (xp, yc)]
        ret = [Bp, (g, yc - o * 0.2), (g, inner - o * extra_in), (vx, vy)]
    elif kind == 'HB':
        A, Bp = (g - R_PITCH * s, yc), (g, yc)
        feed = [(xp, yp), (xp, toe + o * 0.05), A]
        ret = [Bp, (g, inner - o * extra_in), (vx, vy)]
    elif kind == 'V':
        yA = yc
        yB = yA + o * R_PITCH
        A, Bp = (xp, yA), (xp, yB)
        feed = [(xp, yp), (xp, yA)]
        ret = [Bp, (g, yB - o * 0.4), (g, inner - o * extra_in), (vx, vy)]
    else:
        raise ValueError(kind)
    return place_R(net, A, Bp, feed, ret)


def rnd(p):
    return (round(p[0], 4), round(p[1], 4))


def build(Rs, extra):
    plan = dict(remove_tracks=list(extra.get('remove_tracks', [])), add_tracks=list(extra.get('add_tracks', [])),
                remove_vias=list(extra.get('remove_vias', [])), add_vias=list(extra.get('add_vias', [])),
                add_pads=list(extra.get('add_pads', [])), renet_pads=[], move_parts=list(extra.get('move_parts', [])),
                reshape_tracks=list(extra.get('reshape_tracks', [])))
    for net, R in Rs.items():
        plan['remove_tracks'] += old_stub(net)
        plan['add_tracks'] += R['tracks']
        plan['renet_pads'].append(dict(ref='U3', pad=str(DQ_PIN[net]), net='SDRAM-' + net))
        for p in R['pads']:
            plan['add_pads'].append(dict(ref=R['ref'] or 'R_' + net, pad=p['pad'], layer='Bottom', net=p['net'],
                                         x=p['x'], y=p['y'], w=R_PAD, h=R_PAD, shape='rect', hole=0.0))
    return plan


def touched(plan, Rs):
    s = set()
    for k in ('remove_tracks', 'add_tracks', 'remove_vias', 'add_vias'):
        for o in plan.get(k, []):
            s.add(o['net'])
    for m in plan.get('move_parts', []):
        for p in D['pads']:
            if p['ref'] == m['ref'] and p['net']:
                s.add(p['net'])
    for n in Rs:
        s.add(n)
        s.add('SDRAM-' + n)
    return s


if __name__ == "__main__":
    import design_arrays_report
    design_arrays_report.main()
