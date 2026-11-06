# -*- coding: utf-8 -*-
"""Everything the U1 fan-out design needs, read from the PcbDoc and written to
tools/fanout_inputs.json so that every planner works from the same numbers.

    python tools/fanout_inputs.py

WHAT IT WRITES
  balls        every U1 land: name, ring, x, y (mm, board coords), net (or null)
  grid         the 19x19 lattice: row letters, column numbers, pitch, land
  vacant       every unpopulated lattice position with its x, y, ring
  blocked      vacant positions a 0.35 mm via land could NOT occupy because a
               pad on Top (other than U1's) or Bottom, or a through-hole pad,
               comes within land radius + clearance of the cell centre
  nets         for every U1 net: its other pads on the board (refdes, pad,
               layer, x, y) -- the destinations the escape has to reach
  rules        the values in Rules6 that bind the fan-out
  neighbours   copper extents of the parts around U1 (from their pads)

Rings count from the OUTSIDE (ring 0 = row A / row W / col 1 / col 19).
Board coordinates: x right, y up, origin at the board's lower-left corner.
"""
import io
import json
import os
import re
import struct

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbDoc')
OUT = os.path.join(HERE, 'fanout_inputs.json')
U = 2.54e-6
ROWS = 'ABCDEFGHJKLMNPRTUVW'
LAYER = {1: 'Top', 32: 'Bottom', 74: 'Multi'}


def kvs(stream, key):
    f = olefile.OleFileIO(PCB)
    d = f.openstream(stream).read().decode('latin-1', 'replace')
    f.close()
    out = {}
    for i, r in enumerate(x for x in d.split(chr(0)) if key in x):
        kv = {}
        for item in r.strip('|').split('|'):
            if '=' in item:
                k, v = item.split('=', 1)
                kv[k] = v
        out[i] = kv
    return out


def pads():
    nets = {i: kv.get('NAME') for i, kv in kvs('Nets6/Data', 'NAME=').items()}
    comps = {i: kv for i, kv in kvs('Components6/Data', 'SOURCEDESIGNATOR=').items()}
    f = olefile.OleFileIO(PCB)
    d = f.openstream('Pads6/Data').read()
    f.close()
    out = []
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
        layer = b[0]
        net = struct.unpack('<h', b[3:5])[0]
        comp = struct.unpack('<h', b[7:9])[0]
        x = struct.unpack('<i', b[13:17])[0] * U
        y = struct.unpack('<i', b[17:21])[0] * U
        sx = struct.unpack('<i', b[21:25])[0] * U
        sy = struct.unpack('<i', b[25:29])[0] * U
        hole = struct.unpack('<i', b[45:49])[0] * U
        c = comps.get(comp, {})
        out.append(dict(ref=c.get('SOURCEDESIGNATOR'), pattern=c.get('PATTERN'), pad=name,
                        layer=LAYER.get(layer, str(layer)), x=round(x, 4), y=round(y, 4),
                        sx=round(sx, 4), sy=round(sy, 4), hole=round(hole, 4),
                        net=nets.get(net) if net >= 0 else None))
    return out


def rules():
    want = {}
    for kv in kvs('Rules6/Data', 'RULEKIND=').values():
        n = kv.get('NAME')
        if n in ('Clearance', 'Clearance_SDRAM_INNER', 'Clearance_SDRAM_CLK', 'RoutingVias',
                 'HoleToHoleClearance', 'PlaneClearance', 'PlaneConnect', 'PolygonConnect',
                 'Width', 'Width_SDRAM', 'Width_PWR_VCC3V3', 'Width_PWR_U8', 'Width_PWR_VCC1V0',
                 'Width_PWR_RAILS', 'SolderMaskExpansion_Vias', 'SolderMaskExpansion_U1',
                 'MinimumSolderMaskSliver'):
            skip = {'SELECTION', 'LAYER', 'LOCKED', 'POLYGONOUTLINE', 'USERROUTED', 'KEEPOUT',
                    'UNIONINDEX', 'UNIQUEID', 'DEFINEDBYLOGICALDOCUMENT', 'COMMENT'}
            want[n] = {k: v for k, v in kv.items() if k not in skip}
    return want


def main():
    P = pads()
    u1 = [p for p in P if p['ref'] == 'U1']
    land = max(p['sx'] for p in u1)
    xs = sorted(set(p['x'] for p in u1))
    ys = sorted(set(p['y'] for p in u1))
    # lattice: column c -> x, row r -> y (row A is the TOP row on the board, largest y)
    colx = {}
    rowy = {}
    for p in u1:
        r = ROWS.index(p['pad'][0])
        c = int(p['pad'][1:])
        colx.setdefault(c, []).append(p['x'])
        rowy.setdefault(r, []).append(p['y'])
    colx = {c: round(sum(v) / len(v), 4) for c, v in colx.items()}
    rowy = {r: round(sum(v) / len(v), 4) for r, v in rowy.items()}
    # fill any column/row with no ball by interpolation on the 0.5 pitch
    pitch_x = (colx[19] - colx[1]) / 18.0
    pitch_y = (rowy[0] - rowy[18]) / 18.0
    for c in range(1, 20):
        colx.setdefault(c, round(colx[1] + (c - 1) * pitch_x, 4))
    for r in range(19):
        rowy.setdefault(r, round(rowy[0] - r * pitch_y, 4))

    def ring(r, c):
        return min(r, 18 - r, c - 1, 19 - c)

    balls = []
    pop = set()
    for p in u1:
        r = ROWS.index(p['pad'][0])
        c = int(p['pad'][1:])
        pop.add((r, c))
        balls.append(dict(name=p['pad'], row=p['pad'][0], col=c, ring=ring(r, c),
                          x=p['x'], y=p['y'], net=p['net']))
    vacant = []
    for r in range(19):
        for c in range(1, 20):
            if (r, c) not in pop:
                vacant.append(dict(name=ROWS[r] + str(c), row=ROWS[r], col=c, ring=ring(r, c),
                                   x=colx[c], y=rowy[r]))

    # blocked cells: a 0.35 land (radius 0.175) + 0.09 clearance against any pad
    # that exists on Top (not U1), on Bottom, or on every layer, using the pad's
    # rectangle grown by the clearance envelope
    via_r = 0.35 / 2
    clr = 0.09
    others = [p for p in P if p['ref'] != 'U1']
    blocked = []
    for v in vacant:
        hits = []
        for p in others:
            if p['layer'] not in ('Top', 'Bottom', 'Multi'):
                continue
            hx, hy = p['sx'] / 2, p['sy'] / 2
            dx = max(abs(v['x'] - p['x']) - hx, 0.0)
            dy = max(abs(v['y'] - p['y']) - hy, 0.0)
            gap = (dx * dx + dy * dy) ** 0.5 - via_r
            if gap < clr:
                hits.append(dict(ref=p['ref'], pad=p['pad'], layer=p['layer'], gap=round(gap, 4)))
        if hits:
            blocked.append(dict(cell=v['name'], ring=v['ring'], hits=hits))

    # destinations: every other pad of every U1 net
    u1nets = sorted({p['net'] for p in u1 if p['net']})
    nets = {}
    for n in u1nets:
        nets[n] = dict(u1_balls=sorted(p['pad'] for p in u1 if p['net'] == n),
                       others=[dict(ref=p['ref'], pad=p['pad'], layer=p['layer'], x=p['x'], y=p['y'])
                               for p in others if p['net'] == n])

    # neighbour copper extents (from pads), for the parts that border U1
    ext = {}
    for p in others:
        e = ext.setdefault(p['ref'], [9e9, -9e9, 9e9, -9e9, p['layer']])
        e[0] = min(e[0], p['x'] - p['sx'] / 2)
        e[1] = max(e[1], p['x'] + p['sx'] / 2)
        e[2] = min(e[2], p['y'] - p['sy'] / 2)
        e[3] = max(e[3], p['y'] + p['sy'] / 2)
    u1x0, u1x1 = min(p['x'] for p in u1) - land / 2, max(p['x'] for p in u1) + land / 2
    u1y0, u1y1 = min(p['y'] for p in u1) - land / 2, max(p['y'] for p in u1) + land / 2
    near = {}
    for ref, e in ext.items():
        if e[1] > u1x0 - 6 and e[0] < u1x1 + 6 and e[3] > u1y0 - 6 and e[2] < u1y1 + 6:
            near[ref] = dict(x0=round(e[0], 4), x1=round(e[1], 4), y0=round(e[2], 4), y1=round(e[3], 4), layer=e[4])

    out = dict(
        source=os.path.normpath(PCB),
        grid=dict(rows=ROWS, cols=list(range(1, 20)), pitch_x=round(pitch_x, 6), pitch_y=round(pitch_y, 6),
                  land=round(land, 6), col_x=colx, row_y={ROWS[r]: y for r, y in rowy.items()},
                  u1_extent=dict(x0=round(u1x0, 4), x1=round(u1x1, 4), y0=round(u1y0, 4), y1=round(u1y1, 4))),
        balls=balls, vacant=vacant, blocked=blocked, nets=nets, rules=rules(), neighbours=near,
        bottom_pads_under_u1=[dict(ref=p['ref'], pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy'], net=p['net'])
                              for p in others if p['layer'] == 'Bottom'
                              and u1x0 - 0.5 < p['x'] < u1x1 + 0.5 and u1y0 - 0.5 < p['y'] < u1y1 + 0.5],
    )
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, indent=1))
    print('U1: %d balls (%d netted), land %.6f, pitch %.6f x %.6f' % (
        len(balls), sum(1 for b in balls if b['net']), land, pitch_x, pitch_y))
    print('vacant %d, blocked for a 0.35 via: %d -> %s' % (len(vacant), len(blocked), ' '.join(b['cell'] for b in blocked)))
    print('nets on U1: %d; bottom pads under U1: %d; neighbours within 6 mm: %s' % (
        len(nets), len(out['bottom_pads_under_u1']), ' '.join(sorted(near))))
    print('wrote', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
