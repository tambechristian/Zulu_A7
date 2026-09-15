# -*- coding: utf-8 -*-
"""Everything the SDRAM-bus routing needs, read from the PcbDoc AS SAVED (so the
placed fan-out is part of the geometry), written to tools/route_inputs.json.

    python tools/route_inputs.py

WHAT IT WRITES
  nets        the 39 SDRAM nets: for each, its U3 pad(s) on Bottom and its U1
              end as the fan-out left it -- a moat via (ring 2), a Top stub
              whose free end sits 0.10 mm outside the land field (ring 1), or
              the ball itself (ring 0, nothing placed) -- plus the net's class
              and its rule set (width, clearance on L3/L4)
  vias        every via on the board (107): x, y, size, hole, net
  tracks      every track on Top / L3-SIG / L4-SIG / Bottom: net, layer, ends, width
  th_pads     every through-hole pad (copper on every layer): x, y, size, net
  bottom_pads every Bottom SMD pad inside the region (obstacles for Bottom stubs)
  top_pads    every Top SMD pad inside the region
  region      the routing window
  u3          body and pad-row geometry
  rules       the values that bind: SDRAM width table, clearances, via, holes

Pad rotation is the double at byte 52 of the pad body; a 90/270 pad swaps its
size axes on the board.  Via records: layer@0, net int16@3, x@13, y@17,
size@21, hole@25.  Track records: layer@0, net@3, x1@13 y1@17 x2@21 y2@25
width@29.  Coordinates in mm on the board origin, y up.
"""
import io
import json
import os
import struct

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbDoc')
FAN = os.path.join(HERE, 'fanout_plan.json')
OUT = os.path.join(HERE, 'route_inputs.json')
U = 2.54e-6
LAYER = {1: 'Top', 2: 'L3-SIG', 3: 'L4-SIG', 32: 'Bottom', 74: 'Multi'}
# The whole board.  2026-09-15: this was x 14..45, y 3.5..21, which silently dropped U1's
# lands east of x 45 and U4's east pads -- the checker could not see them, and a router
# (astar) had to synthesise them itself.  Nothing is clipped now.
REGION = dict(x0=0.0, x1=69.85, y0=0.0, y1=25.40)

DATA = ['D%d' % k for k in range(16)]
ADDR = ['A%d' % k for k in range(13)] + ['BS0', 'BS1']
CTRL = ['CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM', 'SDRAM-CS#', 'SDRAM-CLK']
CLS = {n: 'SDRAM_DATA' for n in DATA}
CLS.update({n: 'SDRAM_ADDR' for n in ADDR})
CLS.update({n: 'SDRAM_CTRL' for n in CTRL})


def kvs(f, stream, key):
    d = f.openstream(stream).read().decode('latin-1', 'replace')
    out = {}
    for i, r in enumerate(x for x in d.split(chr(0)) if key in x):
        kv = {}
        for item in r.strip('|').split('|'):
            if '=' in item:
                k, v = item.split('=', 1)
                kv[k] = v
        out[i] = kv
    return out


def main():
    f = olefile.OleFileIO(PCB)
    nets = {i: kv.get('NAME') for i, kv in kvs(f, 'Nets6/Data', 'NAME=').items()}
    comps = {i: kv for i, kv in kvs(f, 'Components6/Data', 'SOURCEDESIGNATOR=').items()}

    # ---- pads ---------------------------------------------------------------
    d = f.openstream('Pads6/Data').read()
    pads = []
    i = 0
    while i + 5 <= len(d):
        t = d[i]
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        if t != 2:
            break
        name = d[i + 6:i + 6 + d[i + 5]].decode('latin-1')
        i += 5 + ln
        for k in range(3):
            l2 = struct.unpack('<I', d[i:i + 4])[0]
            i += 4 + l2
        l2 = struct.unpack('<I', d[i:i + 4])[0]
        b = d[i + 4:i + 4 + l2]
        i += 4 + l2
        l2 = struct.unpack('<I', d[i:i + 4])[0]
        i += 4 + l2
        if len(b) < 60:
            continue
        net = struct.unpack('<h', b[3:5])[0]
        comp = struct.unpack('<h', b[7:9])[0]
        x = struct.unpack('<i', b[13:17])[0] * U
        y = struct.unpack('<i', b[17:21])[0] * U
        sx = struct.unpack('<i', b[21:25])[0] * U
        sy = struct.unpack('<i', b[25:29])[0] * U
        hole = struct.unpack('<i', b[45:49])[0] * U
        rot = struct.unpack('<d', b[52:60])[0]
        if round(rot) % 180 == 90:
            sx, sy = sy, sx
        c = comps.get(comp, {})
        pads.append(dict(ref=c.get('SOURCEDESIGNATOR'), pad=name, layer=LAYER.get(b[0], str(b[0])),
                         x=round(x, 4), y=round(y, 4), sx=round(sx, 4), sy=round(sy, 4),
                         hole=round(hole, 4), rot=rot, net=nets.get(net) if net >= 0 else None))

    # ---- vias ---------------------------------------------------------------
    d = f.openstream('Vias6/Data').read()
    vias = []
    i = 0
    while i + 5 <= len(d):
        t = d[i]
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        b = d[i + 5:i + 5 + ln]
        i += 5 + ln
        if t != 3:
            continue
        net = struct.unpack('<h', b[3:5])[0]
        vias.append(dict(x=round(struct.unpack('<i', b[13:17])[0] * U, 4), y=round(struct.unpack('<i', b[17:21])[0] * U, 4),
                         size=round(struct.unpack('<i', b[21:25])[0] * U, 4), hole=round(struct.unpack('<i', b[25:29])[0] * U, 4),
                         net=nets.get(net) if net >= 0 else None))

    # ---- tracks -------------------------------------------------------------
    d = f.openstream('Tracks6/Data').read()
    tracks = []
    i = 0
    while i + 5 <= len(d):
        t = d[i]
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        b = d[i + 5:i + 5 + ln]
        i += 5 + ln
        if t != 4 or b[0] not in LAYER or b[0] == 74:
            continue
        net = struct.unpack('<h', b[3:5])[0]
        tracks.append(dict(layer=LAYER[b[0]], net=nets.get(net) if net >= 0 else None,
                           x1=round(struct.unpack('<i', b[13:17])[0] * U, 4), y1=round(struct.unpack('<i', b[17:21])[0] * U, 4),
                           x2=round(struct.unpack('<i', b[21:25])[0] * U, 4), y2=round(struct.unpack('<i', b[25:29])[0] * U, 4),
                           width=round(struct.unpack('<i', b[29:33])[0] * U, 4)))
    rules = {}
    for kv in kvs(f, 'Rules6/Data', 'RULEKIND=').values():
        if kv.get('NAME') in ('Clearance', 'Clearance_SDRAM_INNER', 'Clearance_SDRAM_CLK', 'RoutingVias',
                              'HoleToHoleClearance', 'Width_SDRAM', 'Width', 'PlaneClearance'):
            rules[kv['NAME']] = {k: v for k, v in kv.items() if k not in (
                'SELECTION', 'LAYER', 'LOCKED', 'POLYGONOUTLINE', 'USERROUTED', 'KEEPOUT', 'UNIONINDEX', 'UNIQUEID',
                'DEFINEDBYLOGICALDOCUMENT', 'COMMENT')}
    f.close()

    fan = json.load(io.open(FAN, encoding='utf-8'))
    ball_action = {b['name']: b for b in fan['balls']}
    u1 = [p for p in pads if p['ref'] == 'U1']
    ball_by_net = {}
    for p in u1:
        if p['net']:
            ball_by_net.setdefault(p['net'], []).append(p)
    lf = dict(x0=min(p['x'] for p in u1) - 0.1125, x1=max(p['x'] for p in u1) + 0.1125,
              y0=min(p['y'] for p in u1) - 0.1125, y1=max(p['y'] for p in u1) + 0.1125)

    def inside(x, y):
        return lf['x0'] <= x <= lf['x1'] and lf['y0'] <= y <= lf['y1']

    out_nets = {}
    for n in DATA + ADDR + CTRL:
        u3p = [dict(pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy']) for p in pads if p['ref'] == 'U3' and p['net'] == n]
        ends = []
        for b in ball_by_net.get(n, []):
            act = ball_action.get(b['pad'], {}).get('action')
            e = dict(ball=b['pad'], ring=ball_action.get(b['pad'], {}).get('ring'), action=act, ball_x=b['x'], ball_y=b['y'])
            if act == 'dogbone-in' or act == 'dogbone-out':
                v = [w for w in vias if w['net'] == n and abs(w['x'] - b['x']) <= 1.6 and abs(w['y'] - b['y']) <= 1.6]
                e.update(kind='via', x=v[0]['x'], y=v[0]['y']) if v else e.update(kind='via-missing')
            elif act == 'gap':
                # the stub segment whose one end lies outside the land field: that end is the free end
                seg = [t for t in tracks if t['net'] == n and t['layer'] == 'Top' and
                       (not inside(t['x1'], t['y1']) or not inside(t['x2'], t['y2']))]
                if seg:
                    t = seg[0]
                    fx, fy = (t['x1'], t['y1']) if not inside(t['x1'], t['y1']) else (t['x2'], t['y2'])
                    e.update(kind='stub-end', x=fx, y=fy, layer='Top')
                else:
                    e.update(kind='stub-missing')
            elif act == 'direct':
                e.update(kind='ball', x=b['x'], y=b['y'], layer='Top')
            else:
                e.update(kind=act or 'unknown')
            ends.append(e)
        cls = CLS[n]
        out_nets[n] = dict(cls=cls, u3=u3p, u1=ends,
                           width=dict(top_min=0.0762, top_pref=0.0762, inner_min=0.10, inner_pref=0.125, inner_max=0.15, bottom_min=0.10, bottom_pref=0.125),
                           clearance=dict(top=0.09, bottom=0.09, inner=0.20 if n == 'SDRAM-CLK' else 0.10))

    inreg = lambda p: REGION['x0'] <= p['x'] <= REGION['x1'] and REGION['y0'] <= p['y'] <= REGION['y1']
    u3pads = [p for p in pads if p['ref'] == 'U3']
    out = dict(
        source=os.path.normpath(PCB), region=REGION, land_field=lf,
        nets=out_nets,
        vias=vias,
        tracks=[t for t in tracks],
        th_pads=[dict(ref=p['ref'], pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy'], hole=p['hole'], net=p['net'])
                 for p in pads if p['layer'] == 'Multi' and inreg(p)],
        bottom_pads=[dict(ref=p['ref'], pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy'], net=p['net'])
                     for p in pads if p['layer'] == 'Bottom' and inreg(p)],
        top_pads=[dict(ref=p['ref'], pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy'], net=p['net'])
                  for p in pads if p['layer'] == 'Top' and inreg(p)],
        u3=dict(rows_y=sorted(set(round(p['y'], 3) for p in u3pads)), x_min=min(p['x'] for p in u3pads), x_max=max(p['x'] for p in u3pads),
                pad_sx=u3pads[0]['sx'], pad_sy=u3pads[0]['sy'], east_copper=max(p['x'] + p['sx'] / 2 for p in u3pads),
                pocket=dict(y0=max(p['y'] + p['sy'] / 2 for p in u3pads if p['y'] < 10), y1=min(p['y'] - p['sy'] / 2 for p in u3pads if p['y'] > 10))),
        rules=rules,
    )
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, indent=1))
    kinds = {}
    for n, v in out_nets.items():
        for e in v['u1']:
            kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    print('nets %d; U1 ends by kind: %s' % (len(out_nets), kinds))
    print('vias %d, tracks %d (%s), th pads in region %d, bottom pads %d, top pads %d' % (
        len(vias), len(tracks), {L: sum(1 for t in tracks if t['layer'] == L) for L in ('Top', 'L3-SIG', 'L4-SIG', 'Bottom')},
        len(out['th_pads']), len(out['bottom_pads']), len(out['top_pads'])))
    print('U3: pad rows y %s, x %.4f..%.4f, pad %.3f x %.3f, east copper %.4f, pocket y %.4f..%.4f' % (
        out['u3']['rows_y'], out['u3']['x_min'], out['u3']['x_max'], out['u3']['pad_sx'], out['u3']['pad_sy'], out['u3']['east_copper'],
        out['u3']['pocket']['y0'], out['u3']['pocket']['y1']))
    missing = [(n, e['ball'], e['kind']) for n, v in out_nets.items() for e in v['u1'] if 'missing' in e['kind'] or e['kind'] == 'unknown']
    print('unresolved U1 ends:', missing)
    print('wrote', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
