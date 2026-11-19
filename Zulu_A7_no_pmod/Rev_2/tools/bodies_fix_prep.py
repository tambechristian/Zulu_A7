"""No-PMOD Rev 2 (2026-11-14): clear the four component-body collisions the 2026-11-14 audit found.

    python tools/bodies_fix_prep.py <board model.json> <out dir>

DRC never checked part bodies (the board has none and the batch DRC skips Component Clearance); tools/body_check.py now
does.  Sites from a scan of every displacement (scratchpad bodies/sites.py: body-body >= 0.15 mm, body over another
part's pad >= 0.10, pad-pad >= 0.15, edge 0.30; fewest vias and tracks under the new pads):

  U4   W25Q128 SOIC-8 208 mil, Top: 0.45 mm north (its body sat 0.14 mm on U1's BGA body; 0.34 mm at worst tolerance).
  R34  742C083 array, Bottom: 0.40 mm east (0.13 mm on U7's SOT-23-5 body).
  U10  93LC46B SOIC-8, Bottom -> TOP, flipped about its origin (pad 1) and moved (+2.18, +0.25): pad 1 (23.165, 18.895).
       Its body sat 0.14 mm under X2's 11-20 header housing (Bottom); no legal Bottom site exists within 30 mm (U3
       south, the housing north, X1's mounting holes east).  The Top site lies east of the microSD card's path.
  X4   battery JST PH: the top-entry SMD B2B-PH-SM4-TB is replaced (user decision 2026-11-14) by the through-hole
       vertical B2B-PH-K-S (KiCad JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical: 0.75 mm holes, 2.0 mm pitch, body 5.9 x 4.5
       with the pin row 1.7 mm from one face).  Footprint JST-B2B-PH-K-S: pad 1 at the origin, pad 2 at (+2, 0), round
       1.30 mm lands; body x -1.95..+3.95, y -2.80..+1.70.  Placed at rotation 180: pad 1 (VBATT) (30.86, 1.80), pad 2
       (GND) (28.86, 1.80), body (26.91..32.81, 0.10..4.60), 2.5 mm clear of U2's south pins (the SMD housing covered
       them by 0.74 mm).

Writes model.json (parts moved, the copper they kill or collide with removed: router input), base_moved.json (base with
only the pads changed, for the judge) and rip.json {'remove', 'remove_vias', 'moves'}.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
CLR = 0.09
X4_PADS = {'1': ('VBATT', 30.86, 1.80), '2': ('GND', 28.86, 1.80)}
X4_LAND, X4_HOLE = 1.15, 0.75      # 1.30 left 0.05 mm bottom mask slivers to C4/C5 (DRC 2026-11-14)


def pbox(p, m=0.0):
    return (p['x'] - p['w'] / 2 - m, p['y'] - p['h'] / 2 - m, p['x'] + p['w'] / 2 + m, p['y'] + p['h'] / 2 + m)


def box_pt(b, x, y):
    return math.hypot(max(b[0] - x, 0, x - b[2]), max(b[1] - y, 0, y - b[3]))


def pad_pt(p, x, y):
    if p['shape'] == 'circle':
        return max(0.0, math.hypot(x - p['x'], y - p['y']) - p['w'] / 2)
    return box_pt(pbox(p), x, y)


def pad_seg(p, t):
    n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.02))
    return min(pad_pt(p, t['x1'] + (t['x2'] - t['x1']) * i / n, t['y1'] + (t['y2'] - t['y1']) * i / n) for i in range(n + 1))


def box_seg_hit(b, t):
    n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.02))
    for i in range(n + 1):
        x, y = t['x1'] + (t['x2'] - t['x1']) * i / n, t['y1'] + (t['y2'] - t['y1']) * i / n
        if b[0] <= x <= b[2] and b[1] <= y <= b[3]:
            return True
    return False


# X4_SIDE=1 (user decision 2026-11-15): X4 is the through-hole side-entry JST S2B-PH-K-S, opening south, pins at y 4.70
# (pin 1 VBATT x 29.36, pin 2 GND x 27.36), housing 1.55 mm past the bottom edge; C137, C138, C152 and R126 move to the
# Bottom sites in route/bodies4/x4side_moves.json (their old spots are under the pins)
X4_SIDE = os.environ.get('X4_SIDE') == '1'
EXTRA = json.load(open(os.path.join(HERE, 'route', 'bodies4', 'x4side_moves.json'))) if X4_SIDE else {}
U10_MSOP = tuple(float(v) for v in os.environ['U10_MSOP'].split(',')) if os.environ.get('U10_MSOP') else None


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    # SKIP_U4=1 (2026-11-14): R34, U10 and X4 go in first; U4's move broke 11 nets threaded between its pads and is
    # worked separately (user decision)
    skip_u4 = os.environ.get('SKIP_U4') == '1'
    refs = (('R34', 'U10', 'X4') if skip_u4 else ('U4', 'R34', 'U10', 'X4')) + tuple(EXTRA)
    old = {r: [dict(p) for p in M['pads'] if p['ref'] == r] for r in refs}
    # ---- pads ------------------------------------------------------------------------------------------------
    for p in M['pads']:
        if p['ref'] == 'U4' and not skip_u4:
            p['y'] = round(p['y'] + 0.45, 4)
        elif p['ref'] == 'R34':
            p['x'] = round(p['x'] + 0.40, 4)
        elif p['ref'] == 'U10' and not U10_MSOP:
            p['x'] = round(2 * 20.9851 - p['x'] + 2.18, 4)
            p['y'] = round(p['y'] + 0.25, 4)
            p['layers'] = ['Top Layer']
    if U10_MSOP:
        # U10 -> MSOP-8 93LC46BT-I/MS on the Bottom (user decision 2026-11-14: the Top site covered X2's pin labels):
        # rotation 180 keeps the SOIC's arrangement (pins 1-4 west, pin 1 lowest; pins 5-8 east, pin 8 lowest)
        cx, cy = U10_MSOP
        net = {p['pad']: p['net'] for p in M['pads'] if p['ref'] == 'U10'}
        M['pads'] = [p for p in M['pads'] if p['ref'] != 'U10']
        for k in range(4):
            for pad, x in ((str(k + 1), cx - 2.1125), (str(8 - k), cx + 2.1125)):
                M['pads'].append({'ref': 'U10', 'pad': pad, 'net': net[pad], 'x': round(x, 4), 'y': round(cy - 0.975 + 0.65 * k, 4),
                                  'shape': 'rect', 'w': 1.625, 'h': 0.4, 'layers': ['Bottom Layer'], 'drill': 0.0, 'plated': False})
    x4p = {'1': ('VBATT', 29.36, 4.70), '2': ('GND', 27.36, 4.70)} if X4_SIDE else X4_PADS
    land = 1.20 if X4_SIDE else X4_LAND
    M['pads'] = [p for p in M['pads'] if p['ref'] != 'X4'] + [
        {'ref': 'X4', 'pad': k, 'net': n, 'x': x, 'y': y, 'shape': 'circle', 'w': land, 'h': land,
         'layers': list(STACK), 'drill': X4_HOLE, 'plated': True} for k, (n, x, y) in sorted(x4p.items())]
    for r, mv in EXTRA.items():
        M['pads'] = [p for p in M['pads'] if p['ref'] != r] + [dict(q) for q in mv['pads']]
    u10 = {p['pad']: (p['x'], p['y']) for p in M['pads'] if p['ref'] == 'U10'}
    assert U10_MSOP or (u10['1'] == (23.1651, 18.895) and u10['5'] == (18.2352, 22.705)), u10
    json.dump(M, open(os.path.join(out, 'base_moved.json'), 'w'))
    new = [p for p in M['pads'] if p['ref'] in old]
    # ---- copper that must go -----------------------------------------------------------------------------------
    rm_t, rm_v = [], []
    # (1) via-in-pad of the old pads (U4 and R34 carry VIPPO; U10's Bottom pads leave the Bottom; X4 had none)
    for r, ps in old.items():
        for p in ps:
            for v in M['vias']:
                if (p['layers'][0] if p['layers'] else 'Top Layer') in v['span'] and pad_pt(p, v['x'], v['y']) < 1e-6 and v not in rm_v:
                    rm_v.append(v)
    # (2) other-net copper too close to a new pad, on the pad's layers; any via whose hole is within 0.24 of an X4 hole
    for p in new:
        L = p['layers'] or STACK
        for t in M['tracks']:
            if t['layer'] in L and t['net'] != p['net'] and pad_seg(p, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
        for v in M['vias']:
            hit = any(l in L for l in v['span']) and v['net'] != p['net'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR
            if p['drill'] and math.hypot(v['x'] - p['x'], v['y'] - p['y']) < (v['hole'] + p['drill']) / 2 + 0.24:
                hit = True
            if p['drill'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR:
                hit = True
            if hit and v not in rm_v:
                rm_v.append(v)
    # (2b) U4's own fan-out is kept: each of its pads gets a 0.45 mm Top jog from the old pad centre (where every
    #      U4 track ends) to the new one; routing U4's nets afresh failed (FLASH-D00/D01/D02 found no path past U1)
    jogs = []
    for p in old.get('U4', []):
        ws = [t['w'] for t in M['tracks'] if t['net'] == p['net'] and t['layer'] == 'Top Layer' and
              any(abs(x - p['x']) < 1e-3 and abs(y - p['y']) < 1e-3 for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])))]
        if ws:
            jogs.append({'net': p['net'], 'layer': 'Top Layer', 'w': min(ws), 'x1': p['x'], 'y1': p['y'],
                         'x2': p['x'], 'y2': round(p['y'] + 0.45, 4)})
    M['tracks'] += jogs
    print('U4 jogs: %d (%s)' % (len(jogs), ', '.join('%s %.3f' % (j['net'], j['w']) for j in jogs)))
    # (3) same-net copper inside a new pad's footprint that belonged to the old geometry (e.g. X4's old SMD feed
    #     under the new lands is harmless and stays; nothing to do)
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    # (4) no stub pruning here: cut tracks keep both halves, so the router bridges a short gap instead of re-routing
    #     whole nets (a first run pruned TCK/TDO/CHAN27 back to their pads, 135 mm); compose_plan prunes what is
    #     left dead once the new copper is in.
    moves = [m for m in [
        {'ref': 'U4', 'x': 43.5505, 'y': 21.755, 'dx': 0.0, 'dy': 0.45},
        {'ref': 'R34', 'x': 11.42, 'y': 19.29, 'dx': 0.40, 'dy': 0.0},
        ({'ref': 'U10', 'x': U10_MSOP[0], 'y': U10_MSOP[1], 'dx': round(U10_MSOP[0] - 20.9851, 4),
          'dy': round(U10_MSOP[1] - 18.645, 4), 'rotation': 180, 'pad1': [round(U10_MSOP[0] - 2.1125, 4), round(U10_MSOP[1] - 0.975, 4)]}
         if U10_MSOP else
         {'ref': 'U10', 'x': 23.1651, 'y': 18.895, 'dx': 2.18, 'dy': 0.25, 'layer': 'Top Layer', 'pad1': [23.1651, 18.895]}),
        ({'ref': 'X4', 'x': 29.36, 'y': 4.70, 'dx': -0.5, 'dy': -0.6, 'rotation': 180, 'pad1': [29.36, 4.70]} if X4_SIDE else
         {'ref': 'X4', 'x': 30.86, 'y': 1.80, 'dx': 1.0, 'dy': -3.50, 'rotation': 180, 'pad1': [30.86, 1.80]}),
    ] if m['ref'] in refs]
    for r, mv in EXTRA.items():          # 0201s: origin = pad centre; rotation as viewed from the top
        o = old[r]
        ox, oy = sum(p['x'] for p in o) / 2, sum(p['y'] for p in o) / 2
        p1 = [q for q in mv['pads'] if q['pad'] == '1'][0]
        m = {'ref': r, 'x': round(ox + mv['dx'], 4), 'y': round(oy + mv['dy'], 4), 'dx': mv['dx'], 'dy': mv['dy'],
             'pad1': [p1['x'], p1['y']]}
        if mv['rot']:
            m['rotation'] = mv['rot']
            m['swap_wh'] = True
        moves.append(m)
    # final pad positions on every move: compose_plan is run on base_moved.json, where they are already applied
    for m in moves:
        m['pad_xy'] = {p['pad']: [p['x'], p['y']] for p in M['pads'] if p['ref'] == m['ref']}
    json.dump(M, open(os.path.join(out, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves, 'jogs': jogs}, open(os.path.join(out, 'rip.json'), 'w'), indent=1)
    nets = sorted({o['net'] for o in rm_t + rm_v})
    print('removed: %d tracks, %d vias on %d nets: %s' % (len(rm_t), len(rm_v), len(nets), nets))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), dict(oc)))


if __name__ == '__main__':
    main()
