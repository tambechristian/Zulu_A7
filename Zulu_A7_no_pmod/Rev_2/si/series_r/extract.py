# -*- coding: utf-8 -*-
"""Series-R planning geometry for Zulu_a7_no_pmod Rev 2 (2026-11-13).  READ-ONLY on the board files.

    python si/series_r/extract.py          (from the Rev_2 folder or anywhere)

Reads the PcbDoc on disk with olefile (Altium may have it open; nothing is written to it) and the
project PcbLib, and writes into si/series_r/ only:

  board_extract.json   every component, pad, track, arc, via (with span), fill, region (Top/Bottom/
                       keep-out/overlay/mask/mechanical in full; L2/L5 pour regions summarised),
                       silk text, polygon, the design rules, per-component outline candidates,
                       the D0-D15 escape analysis, the free-area map near U3's DQ rows, and a
                       cross-check against tools/route/model.json
  region_map.png       Top and Bottom side by side, x 25..50, y 0..25.4, D nets highlighted

Record offsets (Altium binary, little-endian, units 1/10000 mil = 2.54e-6 mm, board origin = Board6
ORIGINX/ORIGINY = 0,0 on this board, so stored coordinates are board coordinates):
  Pads6     6 subrecords; body = 5th: layer@0 net@3 comp@7 x@13 y@17 size top@21/25 mid@29/33
            bottom@37/41 hole@45 shape top/mid/bot@49..51 rot(double)@52
  Vias6     net@3 x@13 y@17 size@21 hole@25 start-layer@29 end-layer@30
  Tracks6   layer@0 flags2@2 (2 = keep-out) net@3 polygon@5 comp@7 x1@13 y1@17 x2@21 y2@25 width@29
  Arcs6     layer@0 flags2@2 net@3 polygon@5 comp@7 cx@13 cy@17 r@21 a0(double)@25 a1@33 width@41
  Fills6    layer@0 flags2@2 net@3 comp@7 x1@13 y1@17 x2@21 y2@25 rot(double)@29
  Texts6    2 subrecords; layer@0 comp@7 x@13 y@17 height@21 rot(double)@27 mirror@35 stroke@36
            comment@40 designator@41; 2nd subrecord = the string
  Regions6  layer@0 flags2@2 net@3 polygon@5 comp@7 holecount@14 props(u32 len + text)@18,
            then u32 n + n x (double x, double y), then holes (u32 n + doubles)
  ShapeBasedRegions6  same header; n+1 extended vertices (u8 round, i32 x, i32 y, i32 cx, i32 cy,
            i32 r, double a0, double a1) = 37 bytes each, holes as doubles
(layouts as tools/fab_facts.py and KiCad's altium_parser_pcb.cpp).
"""
import json
import math
import os
import re
import struct
import sys
from collections import defaultdict

import olefile

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
ROOT = os.path.dirname(os.path.dirname(HERE))                      # .../Rev_2
PROJ = ROOT + '/Imported zulu_a7.PrjPcb'
PCB = PROJ + '/Zulu_a7_no_pmod.PcbDoc'
LIB = PROJ + '/zulu_a7.PcbLib'
MODEL = ROOT + '/tools/route/model.json'
OUT = HERE + '/board_extract.json'
PNG = HERE + '/region_map.png'
U = 2.54e-6
MIL = 0.0254

LAYER = {1: 'Top', 2: 'L3-SIG', 3: 'L4-SIG', 4: 'L2-GND', 5: 'L5-VCC3V3', 32: 'Bottom',
         33: 'TopOverlay', 34: 'BottomOverlay', 35: 'TopPaste', 36: 'BottomPaste', 37: 'TopSolder',
         38: 'BottomSolder', 55: 'DrillGuide', 56: 'KeepOut', 73: 'DrillDrawing', 74: 'Multi'}
for _k in range(16):
    LAYER[57 + _k] = 'Mech%d' % (_k + 1)
STACK = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
COPPER = set(STACK)
MODEL_LAYER = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG',
               'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}
DNETS = ['D%d' % k for k in range(16)]
WIN = dict(x0=25.0, x1=50.0, y0=0.0, y1=25.4)          # the map window
SUBRECS = {1: 1, 2: 6, 3: 1, 4: 1, 5: 2, 6: 1, 11: 1, 12: 1}
# AS4C32M16SB datasheet Rev 1.2 (March 2020) Figure 43, 54-pin TSOP II: D (body length) 22.09/22.22/22.35,
# E (body width) 10.03/10.16/10.29, HE (lead tip to tip) 11.56/11.76/11.96, L (foot) 0.4/0.5/0.6, b 0.25..0.45 mm.
TSOP = dict(D=(22.09, 22.22, 22.35), E=(10.03, 10.16, 10.29), HE=(11.56, 11.76, 11.96), L=(0.4, 0.5, 0.6),
            b=(0.25, 0.35, 0.45), e=0.8,
            source='Datasheet/AllianceMemory_512M_SDRAM_Bdie_AS4C32M16SB-7TXN-6TIN-7BIN_Rev1.2_March2020.pdf Fig. 43')


def i32(b, o):
    return struct.unpack('<i', b[o:o + 4])[0]


def i16(b, o):
    return struct.unpack('<h', b[o:o + 2])[0]


def u16(b, o):
    return struct.unpack('<H', b[o:o + 2])[0]


def dbl(b, o):
    return struct.unpack('<d', b[o:o + 8])[0]


def r4(v):
    return round(v, 4)


def kvparse(s):
    kv = {}
    for item in s.strip('|').split('|'):
        if '=' in item:
            k, v = item.split('=', 1)
            kv[k] = v
    return kv


def kvs(f, stream, key):
    d = f.openstream(stream).read().decode('latin-1', 'replace')
    return [kvparse(r) for r in d.split(chr(0)) if key in r]


def records(data):
    """yield (type, [subrecord bytes...]) for a binary primitive stream"""
    i = 0
    while i + 5 <= len(data):
        t = data[i]
        n = SUBRECS.get(t)
        if n is None:
            raise ValueError('unknown record type %d at %d' % (t, i))
        i += 1
        subs = []
        for _ in range(n):
            ln = struct.unpack('<I', data[i:i + 4])[0]
            subs.append(data[i + 4:i + 4 + ln])
            i += 4 + ln
        yield t, subs


def mil(v):
    v = (v or '').strip()
    if v.endswith('mil'):
        return float(v[:-3]) * MIL
    if v.endswith('mm'):
        return float(v[:-2])
    try:
        return float(v) * MIL
    except ValueError:
        return None


# ------------------------------------------------------------------------------------------- parse
def parse_region(b, extended):
    out = dict(layer=LAYER.get(b[0], str(b[0])), keepout=b[2] == 2, net=i16(b, 3), polygon=u16(b, 5),
               comp=u16(b, 7), holecount=u16(b, 14))
    pl = struct.unpack('<I', b[18:22])[0]
    props = kvparse(b[22:22 + pl].decode('latin-1', 'replace').rstrip(chr(0)))
    out['kind'] = props.get('KIND')
    out['props'] = {k: v for k, v in props.items() if k in ('KIND', 'ISBOARDCUTOUT', 'ISSHAPEBASED', 'KEEPOUTRESTRIC',
                                                           'SUBPOLYINDEX', 'UNIONINDEX', 'NAME')}
    j = 22 + pl
    n = struct.unpack('<I', b[j:j + 4])[0]
    j += 4
    pts = []
    if extended:
        for _ in range(n + 1):
            rnd = b[j]
            x, y, cx, cy, r = (i32(b, j + 1 + 4 * k) for k in range(5))
            a0, a1 = dbl(b, j + 21), dbl(b, j + 29)
            pts.append((x * U, y * U) if not rnd else (x * U, y * U))
            if rnd:
                out.setdefault('arcs', []).append([r4(cx * U), r4(cy * U), r4(r * U), round(a0, 3), round(a1, 3)])
            j += 37
    else:
        for _ in range(n):
            pts.append((dbl(b, j) * U, dbl(b, j + 8) * U))
            j += 16
    holes = []
    for _ in range(out['holecount']):
        if j + 4 > len(b):
            break
        hn = struct.unpack('<I', b[j:j + 4])[0]
        j += 4
        h = []
        for _ in range(hn):
            h.append((dbl(b, j) * U, dbl(b, j + 8) * U))
            j += 16
        holes.append(h)
    out['pts'] = [[r4(x), r4(y)] for x, y in pts]
    out['holes'] = [[[r4(x), r4(y)] for x, y in h] for h in holes]
    out['parse_ok'] = (j == len(b))
    return out


def read_pcbdoc(path):
    f = olefile.OleFileIO(path)
    netlist = [kv.get('NAME') for kv in kvs(f, 'Nets6/Data', 'NAME=')]
    compkv = kvs(f, 'Components6/Data', 'SOURCEDESIGNATOR=')
    netname = lambda k: netlist[k] if 0 <= k < len(netlist) else None
    comps = []
    for i, kv in enumerate(compkv):
        comps.append(dict(index=i, ref=kv.get('SOURCEDESIGNATOR'), x=r4(mil(kv['X'])), y=r4(mil(kv['Y'])),
                          rot=round(float(kv.get('ROTATION', '0')), 3),
                          side='Bottom' if kv.get('LAYER') == 'BOTTOM' else 'Top', footprint=kv.get('PATTERN'),
                          lib=kv.get('SOURCEFOOTPRINTLIBRARY'), comment_on=kv.get('COMMENTON') == 'TRUE',
                          name_on=kv.get('NAMEON') == 'TRUE', height=mil(kv.get('HEIGHT', '0mil'))))
    cref = lambda k: comps[k]['ref'] if 0 <= k < len(comps) else None

    # pads
    d = f.openstream('Pads6/Data').read()
    pads = []
    for t, subs in records(d):
        if t != 2:
            continue
        name = subs[0][1:1 + subs[0][0]].decode('latin-1')
        b = subs[4]
        if len(b) < 60:
            continue
        layer = LAYER.get(b[0], str(b[0]))
        sx, sy = i32(b, 21) * U, i32(b, 25) * U
        rot = dbl(b, 52) % 360.0
        shape = {1: 'round', 2: 'rect', 3: 'octagon'}.get(b[49], str(b[49]))
        # roundrect lives in the 6th subrecord (per-layer shape table): KiCad reads shapes at 29*8 = 232
        ext = subs[5]
        if len(ext) >= 261 and ext[232] == 9:
            shape = 'roundrect'
        c, s = abs(math.cos(math.radians(rot))), abs(math.sin(math.radians(rot)))
        bw, bh = sx * c + sy * s, sx * s + sy * c           # axis-aligned extent with rotation applied
        hx, hy = sx / 2, sy / 2
        a = math.radians(rot)
        corners = [[r4(i32(b, 13) * U + px * math.cos(a) - py * math.sin(a)),
                    r4(i32(b, 17) * U + px * math.sin(a) + py * math.cos(a))]
                   for px, py in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
        pads.append(dict(ref=cref(u16(b, 7)), pad=name, layer=layer, net=netname(i16(b, 3)),
                         x=r4(i32(b, 13) * U), y=r4(i32(b, 17) * U), size_x=r4(sx), size_y=r4(sy), rot=round(rot, 3),
                         w=r4(bw), h=r4(bh), shape=shape, hole=r4(i32(b, 45) * U),
                         size_mid=[r4(i32(b, 29) * U), r4(i32(b, 33) * U)],
                         size_bot=[r4(i32(b, 37) * U), r4(i32(b, 41) * U)],
                         corners=corners if (round(rot) % 90) else None))

    vias = []
    for t, subs in records(f.openstream('Vias6/Data').read()):
        b = subs[0]
        lo, hi = sorted((STACK.index(LAYER[b[29]]), STACK.index(LAYER[b[30]])))
        vias.append(dict(net=netname(i16(b, 3)), x=r4(i32(b, 13) * U), y=r4(i32(b, 17) * U), size=r4(i32(b, 21) * U),
                         hole=r4(i32(b, 25) * U), span=STACK[lo:hi + 1],
                         kind='through' if (lo, hi) == (0, 5) else ('micro' if hi - lo == 1 else 'buried/blind')))

    tracks = []
    for t, subs in records(f.openstream('Tracks6/Data').read()):
        b = subs[0]
        tracks.append(dict(layer=LAYER.get(b[0], str(b[0])), keepout=b[2] == 2, net=netname(i16(b, 3)),
                           polygon=u16(b, 5), comp=cref(u16(b, 7)),
                           x1=r4(i32(b, 13) * U), y1=r4(i32(b, 17) * U), x2=r4(i32(b, 21) * U), y2=r4(i32(b, 25) * U),
                           w=r4(i32(b, 29) * U)))

    arcs = []
    for t, subs in records(f.openstream('Arcs6/Data').read()):
        b = subs[0]
        arcs.append(dict(layer=LAYER.get(b[0], str(b[0])), keepout=b[2] == 2, net=netname(i16(b, 3)),
                         polygon=u16(b, 5), comp=cref(u16(b, 7)), cx=r4(i32(b, 13) * U), cy=r4(i32(b, 17) * U),
                         r=r4(i32(b, 21) * U), a0=round(dbl(b, 25), 3), a1=round(dbl(b, 33), 3), w=r4(i32(b, 41) * U)))

    fills = []
    for t, subs in records(f.openstream('Fills6/Data').read()):
        b = subs[0]
        fills.append(dict(layer=LAYER.get(b[0], str(b[0])), keepout=b[2] == 2, net=netname(i16(b, 3)),
                          comp=cref(u16(b, 7)), x1=r4(i32(b, 13) * U), y1=r4(i32(b, 17) * U),
                          x2=r4(i32(b, 21) * U), y2=r4(i32(b, 25) * U), rot=round(dbl(b, 29), 3)))

    texts = []
    for t, subs in records(f.openstream('Texts6/Data').read()):
        b = subs[0]
        s = subs[1]
        txt = s[4:4 + struct.unpack('<I', s[:4])[0]].decode('latin-1', 'replace') if len(s) >= 4 else ''
        txt = txt.rstrip(chr(0))
        if not txt and len(s):
            txt = s[1:1 + s[0]].decode('latin-1', 'replace')
        comp = cref(u16(b, 7))
        isc, isd = b[40] == 1, b[41] == 1
        hidden = False
        if comp is not None:
            cc = comps[u16(b, 7)]
            hidden = (isd and not cc['name_on']) or (isc and not cc['comment_on'])
        texts.append(dict(layer=LAYER.get(b[0], str(b[0])), comp=comp, x=r4(i32(b, 13) * U), y=r4(i32(b, 17) * U),
                          height=r4(i32(b, 21) * U), rot=round(dbl(b, 27), 3), mirror=b[35] == 1,
                          stroke=r4(i32(b, 36) * U), designator=isd, comment=isc, hidden=hidden, text=txt))

    regions = [parse_region(subs[0], False) for t, subs in records(f.openstream('Regions6/Data').read())]
    sregions = [parse_region(subs[0], True) for t, subs in records(f.openstream('ShapeBasedRegions6/Data').read())]
    for r in regions + sregions:
        r['net'] = netname(r['net'])
        r['comp'] = cref(r['comp'])
    polygons = []
    for kv in kvs(f, 'Polygons6/Data', 'POLYGONTYPE='):
        nm = kv.get('NAME', '')
        try:
            nm = ''.join(chr(int(c)) for c in nm.split(',')) if re.fullmatch(r'[\d,]+', nm) else nm
        except ValueError:
            pass
        verts = []
        k = 0
        while 'VX%d' % k in kv:
            verts.append([r4(mil(kv['VX%d' % k])), r4(mil(kv['VY%d' % k]))])
            k += 1
        polygons.append(dict(name=nm, layer=kv.get('LAYER'), net=netname(int(kv.get('NET', '-1'))),
                             type=kv.get('POLYGONTYPE'), pour_over=kv.get('POUROVER'), remove_dead=kv.get('REMOVEDEAD'),
                             hatch=kv.get('HATCHSTYLE'), track_width=mil(kv.get('TRACKWIDTH')), outline=verts))
    rules = kvs(f, 'Rules6/Data', 'RULEKIND=')
    classes = [kv for kv in kvs(f, 'Classes6/Data', 'NAME=')]
    board = kvparse(f.openstream('Board6/Data').read().decode('latin-1', 'replace').replace(chr(0), '|'))
    f.close()
    return dict(nets=netlist, comps=comps, pads=pads, vias=vias, tracks=tracks, arcs=arcs, fills=fills, texts=texts,
                regions=regions, sregions=sregions, polygons=polygons, rules=rules, classes=classes, board=board)


def read_pcblib(path):
    """footprints in the project PcbLib: names, and any ComponentBody (type 12) / courtyard-ish primitives"""
    f = olefile.OleFileIO(path)
    out = {}
    for parts in f.listdir():
        if len(parts) != 2 or parts[1] != 'Data' or parts[0] in ('Library', 'FileVersionInfo'):
            continue
        d = f.openstream('/'.join(parts)).read()
        ln = struct.unpack('<I', d[:4])[0]
        name = d[5:5 + d[4]].decode('latin-1') if ln else parts[0]
        rec = defaultdict(int)
        bodies, mech = [], []
        try:
            for t, subs in records(d[4 + ln:]):
                rec[t] += 1
                b = subs[0]
                if t == 12:
                    pl = struct.unpack('<I', b[18:22])[0] if len(b) > 22 else 0
                    bodies.append(dict(layer=LAYER.get(b[0], str(b[0])), props=kvparse(b[22:22 + pl].decode('latin-1', 'replace'))))
                elif t == 4 and LAYER.get(b[0], '').startswith(('Mech', 'TopOverlay', 'BottomOverlay')):
                    mech.append(dict(layer=LAYER.get(b[0]), x1=r4(i32(b, 13) * U), y1=r4(i32(b, 17) * U),
                                     x2=r4(i32(b, 21) * U), y2=r4(i32(b, 25) * U), w=r4(i32(b, 29) * U)))
            ok = True
        except Exception as e:      # noqa: BLE001
            ok = 'parse stopped: %s' % e
        out[name] = dict(record_counts={str(k): v for k, v in rec.items()}, bodies=bodies, outline_prims=len(mech),
                         parse_ok=ok)
    f.close()
    return out


# ------------------------------------------------------------------------------------------- geometry
def seg_pt(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)


def pad_contains(p, x, y, tol=1e-3):
    a = math.radians(-p['rot'])
    dx, dy = x - p['x'], y - p['y']
    lx, ly = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
    if p['shape'] == 'round':
        r = min(p['size_x'], p['size_y']) / 2
        ex, ey = max(p['size_x'] / 2 - r, 0), max(p['size_y'] / 2 - r, 0)
        return math.hypot(max(abs(lx) - ex, 0), max(abs(ly) - ey, 0)) <= r + tol
    return abs(lx) <= p['size_x'] / 2 + tol and abs(ly) <= p['size_y'] / 2 + tol


def pad_layers(p):
    return STACK if p['layer'] == 'Multi' else [p['layer']]


def net_graph(B, net):
    """connectivity graph of one net's copper: nodes ('t', i) / ('v', i) / ('p', i)"""
    T = [(i, t) for i, t in enumerate(B['tracks']) if t['net'] == net and t['layer'] in COPPER and t['polygon'] == 65535]
    V = [(i, v) for i, v in enumerate(B['vias']) if v['net'] == net]
    P = [(i, p) for i, p in enumerate(B['pads']) if p['net'] == net]
    adj = defaultdict(set)

    def link(a, b):
        adj[a].add(b)
        adj[b].add(a)
    for i, t in T:
        ends = ((t['x1'], t['y1']), (t['x2'], t['y2']))
        for j, u in T:
            if j <= i or u['layer'] != t['layer']:
                continue
            ue = ((u['x1'], u['y1']), (u['x2'], u['y2']))
            if any(seg_pt(u['x1'], u['y1'], u['x2'], u['y2'], *e) <= u['w'] / 2 + 1e-3 for e in ends) or \
               any(seg_pt(t['x1'], t['y1'], t['x2'], t['y2'], *e) <= t['w'] / 2 + 1e-3 for e in ue):
                link(('t', i), ('t', j))
        for j, v in V:
            if t['layer'] in v['span'] and seg_pt(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= v['size'] / 2 + 1e-3:
                link(('t', i), ('v', j))
        for j, p in P:
            if t['layer'] in pad_layers(p) and any(pad_contains(p, *e) for e in ends):
                link(('t', i), ('p', j))
    for i, v in V:
        for j, p in P:
            if set(v['span']) & set(pad_layers(p)) and pad_contains(p, v['x'], v['y']):
                link(('v', i), ('p', j))
        for j, w in V:
            if j > i and math.hypot(v['x'] - w['x'], v['y'] - w['y']) < 1e-3:
                link(('v', i), ('v', j))
    return T, V, P, adj


def describe(B, node):
    k, i = node
    if k == 't':
        t = B['tracks'][i]
        return dict(kind='track', layer=t['layer'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], w=t['w'],
                    length=r4(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])))
    if k == 'v':
        v = B['vias'][i]
        return dict(kind='via', x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=v['span'], via_kind=v['kind'])
    p = B['pads'][i]
    return dict(kind='pad', ref=p['ref'], pad=p['pad'], layer=p['layer'], x=p['x'], y=p['y'], w=p['w'], h=p['h'])


def escapes(B):
    out = {}
    for net in DNETS:
        T, V, P, adj = net_graph(B, net)
        start = [('p', i) for i, p in P if p['ref'] == 'U3']
        goal = {('p', i) for i, p in P if p['ref'] == 'U1'}
        prev = {start[0]: None}
        q = [start[0]]
        while q:
            n = q.pop(0)
            for m in sorted(adj[n]):
                if m not in prev:
                    prev[m] = n
                    q.append(m)
        g = [n for n in goal if n in prev]
        path = []
        if g:
            n = g[0]
            while n is not None:
                path.append(n)
                n = prev[n]
            path.reverse()
        # orient each track along the path
        seq = []
        cur = None
        for n in path:
            dsc = describe(B, n)
            if dsc['kind'] == 'pad' or dsc['kind'] == 'via':
                cur = (dsc['x'], dsc['y'])
            elif cur is not None:
                if math.hypot(dsc['x2'] - cur[0], dsc['y2'] - cur[1]) < math.hypot(dsc['x1'] - cur[0], dsc['y1'] - cur[1]):
                    dsc['x1'], dsc['y1'], dsc['x2'], dsc['y2'] = dsc['x2'], dsc['y2'], dsc['x1'], dsc['y1']
                cur = (dsc['x2'], dsc['y2'])
            seq.append(dsc)
        on_path = set(path)
        branches = [describe(B, ('t', i)) for i, t in T if ('t', i) not in on_path] + \
                   [describe(B, ('v', i)) for i, v in V if ('v', i) not in on_path]
        u3 = B['pads'][start[0][1]]
        first_via = next((s for s in seq if s['kind'] == 'via'), None)
        i_fv = seq.index(first_via) if first_via else None
        stub = [s for s in seq[1:i_fv] if s['kind'] == 'track'] if first_via else []
        after = seq[i_fv + 1:] if first_via else []
        nxt = next((s for s in after if s['kind'] == 'track'), None)
        top_run = []
        for s in after:
            if s['kind'] == 'track' and s['layer'] == 'Top':
                top_run.append(s)
            elif s['kind'] == 'track' and top_run:
                break
            elif s['kind'] in ('via', 'pad') and top_run:
                top_run.append(s)
                break
        layers_len = defaultdict(float)
        for s in seq:
            if s['kind'] == 'track':
                layers_len[s['layer']] += s['length']
        out[net] = dict(
            u3_pad=dict(pad=u3['pad'], x=u3['x'], y=u3['y'], w=u3['w'], h=u3['h']),
            u1_ball=next((dict(pad=B['pads'][i]['pad'], x=B['pads'][i]['x'], y=B['pads'][i]['y']) for k, i in path if k == 'p' and B['pads'][i]['ref'] == 'U1'), None),
            connected=bool(g),
            bottom_stub=stub, bottom_stub_length=r4(sum(s['length'] for s in stub)),
            first_via=first_via, next_segment_layer=nxt['layer'] if nxt else None,
            top_run_after_first_via=top_run,
            path=seq, path_length_by_layer={k: r4(v) for k, v in layers_len.items()},
            path_length_total=r4(sum(layers_len.values())), vias_on_path=sum(1 for s in seq if s['kind'] == 'via'),
            branches_off_path=branches)
    return out


# ------------------------------------------------------------------------------------------- outlines
def comp_outlines(B):
    """per component: pad extent, silk extent, mechanical/keep-out extent (all from the PcbDoc, by owner)"""
    acc = defaultdict(lambda: defaultdict(list))
    for p in B['pads']:
        if p['ref']:
            acc[p['ref']]['pads'].append((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2))
    for t in B['tracks']:
        if t['comp'] and t['layer'] not in COPPER:
            acc[t['comp']][t['layer']].append((min(t['x1'], t['x2']) - t['w'] / 2, min(t['y1'], t['y2']) - t['w'] / 2,
                                                max(t['x1'], t['x2']) + t['w'] / 2, max(t['y1'], t['y2']) + t['w'] / 2))
    for a in B['arcs']:
        if a['comp'] and a['layer'] not in COPPER:
            rr = a['r'] + a['w'] / 2
            acc[a['comp']][a['layer']].append((a['cx'] - rr, a['cy'] - rr, a['cx'] + rr, a['cy'] + rr))
    for r in B['regions']:
        if r['comp'] and r['pts'] and r['layer'] not in COPPER:
            xs, ys = [q[0] for q in r['pts']], [q[1] for q in r['pts']]
            acc[r['comp']][r['layer'] + '(region)'].append((min(xs), min(ys), max(xs), max(ys)))
    out = {}
    for ref, layers in acc.items():
        out[ref] = {L: [r4(min(b[0] for b in bs)), r4(min(b[1] for b in bs)), r4(max(b[2] for b in bs)), r4(max(b[3] for b in bs))]
                    for L, bs in layers.items()}
    return out


def u3_body(B):
    u3p = [p for p in B['pads'] if p['ref'] == 'U3']
    rows = sorted(set(p['y'] for p in u3p))
    xs = [p['x'] for p in u3p]
    cx = (min(xs) + max(xs)) / 2
    cy = (rows[0] + rows[-1]) / 2
    res = {}
    for k, idx in (('min', 0), ('nom', 1), ('max', 2)):
        D, E = TSOP['D'][idx], TSOP['E'][idx]
        res[k] = dict(x0=r4(cx - D / 2), x1=r4(cx + D / 2), y0=r4(cy - E / 2), y1=r4(cy + E / 2))
    pad_h = u3p[0]['h']
    return dict(source=TSOP['source'] + '; centred on the pad-field centre measured from the PcbDoc',
                pad_field_centre=[r4(cx), r4(cy)], row_y=rows, row_pitch=r4(rows[-1] - rows[0]),
                pad_x_span=[min(xs), max(xs)], pad_size=[u3p[0]['w'], pad_h],
                pad_inner_edges=[r4(rows[0] + pad_h / 2), r4(rows[-1] - pad_h / 2)],
                pad_outer_edges=[r4(rows[0] - pad_h / 2), r4(rows[-1] + pad_h / 2)],
                body=res, lead_tip_span_nom=[r4(cy - TSOP['HE'][1] / 2), r4(cy + TSOP['HE'][1] / 2)],
                datasheet=TSOP)


# ------------------------------------------------------------------------------------------- free-area map
GRID = 0.02
# a part's outline proxy = its pads plus the documentation primitives it owns.  This board came from EAGLE: there are
# NO Top/Bottom Overlay tracks or arcs (silk is text only), the package drawings live on Mech3/Mech4/Mech7/Mech8
# (Mech11/Mech12 are glue dots, left out), and no 3D bodies exist.
# Measured on this board: Mech3/Mech4 hold the package BODY drawings (U2 Mech3 = 10.13 x 10.13 = the LQFP64 10 x 10 body;
# R0402 Mech4 = 0.64 x 0.60), Mech7/Mech8 a larger outline (C0402 3.13 x 1.13, U1 11.1 x 11.1 around the 10 x 10 BGA):
# a courtyard-like / placement outline.  X2 (ZULU-DIP37, the 37 castellated edge pins) owns a board-sized Mech3 region
# and Mech7 outline, so only its pads are used.
BODY_LAYERS = ('pads', 'Mech3', 'Mech4', 'Mech3(region)', 'Mech4(region)')
COURT_LAYERS = ('pads', 'Mech7', 'Mech8', 'Mech7(region)', 'Mech8(region)')
COMP_GAP = 0.254          # ComponentClearance rule (Rules6), horizontal and vertical
CU_GAP = 0.09             # Clearance rule 'Clearance' (All/All) -- binds on Top and Bottom


def raster(B, side, outlines, body, include_bodies=True):
    import numpy as np
    nx = int(round((WIN['x1'] - WIN['x0']) / GRID))
    ny = int(round((WIN['y1'] - WIN['y0']) / GRID))
    xs = WIN['x0'] + (np.arange(nx) + 0.5) * GRID
    ys = WIN['y0'] + (np.arange(ny) + 0.5) * GRID
    X, Y = np.meshgrid(xs, ys)
    cu = np.full((ny, nx), -1.0)           # copper-occupied: value = clearance-free distance helper (unused)
    occ = np.zeros((ny, nx), bool)
    dist = np.full((ny, nx), 99.0)         # distance from cell centre to nearest copper edge (0 inside)

    def upd_seg(x1, y1, x2, y2, hw):
        bx0, bx1 = min(x1, x2) - hw - 1.0, max(x1, x2) + hw + 1.0
        by0, by1 = min(y1, y2) - hw - 1.0, max(y1, y2) + hw + 1.0
        i0, i1 = max(int((bx0 - WIN['x0']) / GRID), 0), min(int((bx1 - WIN['x0']) / GRID) + 1, nx)
        j0, j1 = max(int((by0 - WIN['y0']) / GRID), 0), min(int((by1 - WIN['y0']) / GRID) + 1, ny)
        if i0 >= i1 or j0 >= j1:
            return
        px, py = X[j0:j1, i0:i1], Y[j0:j1, i0:i1]
        vx, vy = x2 - x1, y2 - y1
        L2 = vx * vx + vy * vy
        t = np.zeros_like(px) if L2 == 0 else np.clip(((px - x1) * vx + (py - y1) * vy) / L2, 0, 1)
        dd = np.hypot(x1 + t * vx - px, y1 + t * vy - py) - hw
        dist[j0:j1, i0:i1] = np.minimum(dist[j0:j1, i0:i1], np.maximum(dd, 0))

    def upd_rect(cx, cy, sx, sy, rot, rnd=0.0):
        bx = (sx + sy) / 2 + 1.0
        i0, i1 = max(int((cx - bx - WIN['x0']) / GRID), 0), min(int((cx + bx - WIN['x0']) / GRID) + 1, nx)
        j0, j1 = max(int((cy - bx - WIN['y0']) / GRID), 0), min(int((cy + bx - WIN['y0']) / GRID) + 1, ny)
        if i0 >= i1 or j0 >= j1:
            return
        a = math.radians(-rot)
        dx, dy = X[j0:j1, i0:i1] - cx, Y[j0:j1, i0:i1] - cy
        lx, ly = np.abs(dx * math.cos(a) - dy * math.sin(a)), np.abs(dx * math.sin(a) + dy * math.cos(a))
        ex, ey = sx / 2 - rnd, sy / 2 - rnd
        dd = np.hypot(np.maximum(lx - ex, 0), np.maximum(ly - ey, 0)) - rnd
        dist[j0:j1, i0:i1] = np.minimum(dist[j0:j1, i0:i1], np.maximum(dd, 0))

    for t in B['tracks']:
        if t['layer'] == side:
            upd_seg(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)
    for a in B['arcs']:
        if a['layer'] == side:
            n = 24
            a0, a1 = math.radians(a['a0']), math.radians(a['a1'])
            if a1 <= a0:
                a1 += 2 * math.pi
            pts = [(a['cx'] + a['r'] * math.cos(a0 + (a1 - a0) * k / n), a['cy'] + a['r'] * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                upd_seg(x1, y1, x2, y2, a['w'] / 2)
    for v in B['vias']:
        if side in v['span']:
            upd_seg(v['x'], v['y'], v['x'], v['y'], v['size'] / 2)
    for p in B['pads']:
        if p['layer'] == side or p['layer'] == 'Multi':
            sx, sy = (p['size_x'], p['size_y']) if p['layer'] != 'Bottom' else (p['size_x'], p['size_y'])
            rnd = min(sx, sy) / 2 if p['shape'] == 'round' else 0.0
            upd_rect(p['x'], p['y'], sx, sy, p['rot'], rnd)
            if p['hole'] > 0:
                upd_seg(p['x'], p['y'], p['x'], p['y'], p['hole'] / 2)
    from matplotlib.path import Path
    for r in B['regions'] + B['sregions']:
        if r['layer'] == side and r['pts'] and not r['keepout']:
            rx, ry = [q[0] for q in r['pts']], [q[1] for q in r['pts']]
            i0, i1 = max(int((min(rx) - WIN['x0']) / GRID), 0), min(int((max(rx) - WIN['x0']) / GRID) + 2, nx)
            j0, j1 = max(int((min(ry) - WIN['y0']) / GRID), 0), min(int((max(ry) - WIN['y0']) / GRID) + 2, ny)
            if i0 >= i1 or j0 >= j1:
                continue
            sub = np.c_[X[j0:j1, i0:i1].ravel(), Y[j0:j1, i0:i1].ravel()]
            m = Path(r['pts']).contains_points(sub).reshape(j1 - j0, i1 - i0)
            dist[j0:j1, i0:i1][m] = 0
    copper = dist <= 1e-9
    # parts on this side: pad extent unioned with their silk/mech extent (a conservative body proxy)
    parts = np.zeros_like(copper)          # bodies inflated by the component clearance
    court = np.zeros_like(copper)          # courtyard proxy, not inflated
    plist = []
    for c in B['comps']:
        if c['side'] != side or c['ref'] not in outlines:
            continue
        o = outlines[c['ref']]
        layers_b = ('pads',) if c['ref'] == 'X2' else BODY_LAYERS
        layers_c = ('pads',) if c['ref'] == 'X2' else COURT_LAYERS
        bs = [v for k, v in o.items() if k in layers_b]
        cs = [v for k, v in o.items() if k in layers_c] or [v for k, v in o.items() if k in layers_b]
        if not bs:
            continue
        box = [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]
        cbox = [min(b[0] for b in cs), min(b[1] for b in cs), max(b[2] for b in cs), max(b[3] for b in cs)]
        src = 'pads+Mech3/4 body drawing' if c['ref'] != 'X2' else 'pads only (X2 outline is the whole board)'
        if c['ref'] == 'U3':
            bb = body['body']['max']
            box = [bb['x0'], min(bb['y0'], box[1]), bb['x1'], max(bb['y1'], box[3])]   # body (datasheet max) + lead/pad rows
            src = 'datasheet max body 22.35 x 10.29 + the pad rows (PcbDoc)'
        plist.append(dict(ref=c['ref'], footprint=c['footprint'], box=[r4(v) for v in box], courtyard_proxy=[r4(v) for v in cbox],
                          source=src))
        if include_bodies:
            x0, y0, x1, y1 = box
            if c['ref'] == 'X2':
                continue        # X2's pads are already copper obstacles
            parts |= (X >= x0 - COMP_GAP) & (X <= x1 + COMP_GAP) & (Y >= y0 - COMP_GAP) & (Y <= y1 + COMP_GAP)
            x0, y0, x1, y1 = cbox
            court |= (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
    return dict(X=X, Y=Y, dist=dist, copper=copper, parts=parts, court=court, plist=plist)


def max_rects(free, X, Y, min_w=0.3, min_h=0.3, n=40, zone=None):
    """greedy: repeatedly take the largest empty axis-aligned rectangle (histogram method), carve it out"""
    import numpy as np
    F = free.copy()
    if zone is not None:
        F &= zone
        jj, ii = np.nonzero(zone)
        F, X, Y = F[jj.min():jj.max() + 1, ii.min():ii.max() + 1], X[jj.min():jj.max() + 1, ii.min():ii.max() + 1], Y[jj.min():jj.max() + 1, ii.min():ii.max() + 1]
    # 2x2 block reduce (conservative: a coarse cell is free only if all four fine cells are)
    k = 2
    ny, nx = (F.shape[0] // k) * k, (F.shape[1] // k) * k
    F = F[:ny, :nx].reshape(ny // k, k, nx // k, k).all(axis=(1, 3))
    X = X[:ny, :nx].reshape(ny // k, k, nx // k, k).mean(axis=(1, 3))
    Y = Y[:ny, :nx].reshape(ny // k, k, nx // k, k).mean(axis=(1, 3))
    G = GRID * k
    out = []
    ny, nx = F.shape
    for _ in range(n):
        h = np.zeros(nx, int)
        best = (0, None)
        for j in range(ny):
            h = np.where(F[j], h + 1, 0)
            st = []
            for i in range(nx + 1):
                cur = h[i] if i < nx else 0
                s = i
                while st and st[-1][1] >= cur:
                    s, hh = st.pop()
                    w = i - s
                    # score by the smaller side so long thin slivers do not win
                    if hh * G >= min_h and w * G >= min_w:
                        area = min(w, hh * 3) * min(hh, w * 3)
                        if area > best[0]:
                            best = (area, (s, j - hh + 1, i - 1, j))
                st.append((s, cur))
        if best[1] is None:
            break
        i0, j0, i1, j1 = best[1]
        F[j0:j1 + 1, i0:i1 + 1] = False
        x0, x1 = X[0, i0] - G / 2, X[0, i1] + G / 2
        y0, y1 = Y[j0, 0] - G / 2, Y[j1, 0] + G / 2
        out.append([r4(x0), r4(y0), r4(x1), r4(y1), r4(x1 - x0), r4(y1 - y0)])
    return out


# ------------------------------------------------------------------------------------------- rules
RULE_KINDS = ('Clearance', 'Width', 'ComponentClearance', 'SolderMaskExpansion', 'PasteMaskExpansion',
              'MinimumSolderMaskSliver', 'SilkToSolderMaskClearance', 'SilkToSilkClearance', 'SilkToBoardRegionClearance',
              'HoleToHoleClearance', 'HoleSize', 'RoutingVias', 'PlaneClearance', 'PolygonConnect', 'PlaneConnect',
              'MinimumAnnularRing', 'Height', 'ShortCircuit', 'RoutingLayers', 'RoutingCorners', 'DiffPairsRouting',
              'NetAntennae', 'UnRoutedNet', 'FanoutControl')
DROP = ('SELECTION', 'LAYER', 'LOCKED', 'POLYGONOUTLINE', 'USERROUTED', 'KEEPOUT', 'UNIONINDEX', 'UNIQUEID',
        'DEFINEDBYLOGICALDOCUMENT', 'PRIMITIVELOCK')


def rules_out(B):
    out = []
    for kv in B['rules']:
        if kv.get('RULEKIND') in RULE_KINDS:
            out.append({k: v for k, v in kv.items() if k not in DROP and not k.startswith('V7_')})
    out.sort(key=lambda r: (r.get('RULEKIND'), int(r.get('PRIORITY', 99))))
    return out


def rules_summary(rules):
    """the values that bind a new 0201/0402 series resistor on a D net, in mm"""
    s = {}
    for r in rules:
        k, n = r.get('RULEKIND'), r.get('NAME')
        e = dict(scope1=r.get('SCOPE1EXPRESSION'), scope2=r.get('SCOPE2EXPRESSION'), priority=r.get('PRIORITY'),
                 enabled=r.get('ENABLED'))
        for key, val in r.items():
            if key in ('NAME', 'RULEKIND', 'SCOPE1EXPRESSION', 'SCOPE2EXPRESSION', 'PRIORITY', 'ENABLED', 'COMMENT',
                       'SCOPE1_0_KIND', 'SCOPE1_0_VALUE', 'SCOPE2_0_KIND', 'SCOPE2_0_VALUE', 'NETSCOPE', 'LAYERKIND'):
                continue
            mv = mil(val) if re.fullmatch(r'-?[\d.]+(mil|mm)', val or '') else None
            e[key] = r4(mv) if mv is not None else val
        s['%s | %s' % (k, n)] = e
    return s


# ------------------------------------------------------------------------------------------- model.json cross-check
def crosscheck(B):
    if not os.path.exists(MODEL):
        return dict(error='model.json missing')
    M = json.load(open(MODEL))
    res = {}
    for net in DNETS:
        mt = sorted((MODEL_LAYER[t['layer']], round(t['w'], 3), *sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))]))
                    for t in M['tracks'] if t['net'] == net)
        bt = sorted((t['layer'], round(t['w'], 3), *sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))]))
                    for t in B['tracks'] if t['net'] == net and t['layer'] in COPPER and t['polygon'] == 65535)
        mv = sorted((round(v['x'], 3), round(v['y'], 3), round(v['size'], 3), round(v['hole'], 3), tuple(MODEL_LAYER[s] for s in v['span']))
                    for v in M['vias'] if v['net'] == net)
        bv = sorted((round(v['x'], 3), round(v['y'], 3), round(v['size'], 3), round(v['hole'], 3), tuple(v['span']))
                    for v in B['vias'] if v['net'] == net)
        mp = sorted((p['ref'], p['pad'], round(p['x'], 3), round(p['y'], 3)) for p in M['pads'] if p['net'] == net)
        bp = sorted((p['ref'], p['pad'], round(p['x'], 3), round(p['y'], 3)) for p in B['pads'] if p['net'] == net)

        def near(a, b, tol=0.002):
            return len(a) == len(b) and all(x == y if not isinstance(x, (int, float)) else abs(x - y) <= tol
                                            for x, y in zip(flat(a), flat(b)))

        def flat(seq):
            for s in seq:
                if isinstance(s, (tuple, list)):
                    yield from flat(s)
                else:
                    yield s
        only_m = [t for t in mt if not any(near([t], [u]) for u in bt)]
        only_b = [t for t in bt if not any(near([t], [u]) for u in mt)]
        res[net] = dict(tracks_model=len(mt), tracks_pcbdoc=len(bt), vias_model=len(mv), vias_pcbdoc=len(bv),
                        pads_model=len(mp), pads_pcbdoc=len(bp),
                        tracks_only_in_model=only_m, tracks_only_in_pcbdoc=only_b,
                        vias_identical=near(mv, bv), pads_identical=near(mp, bp),
                        vias_only_in_model=[v for v in mv if v not in bv], vias_only_in_pcbdoc=[v for v in bv if v not in mv])
    return res


# ------------------------------------------------------------------------------------------- per-DQ local room
def copper_dist(B, layer, x, y, skip_net=None):
    """nearest other-net copper edge on a layer from point (x, y): (distance, description)"""
    best = (99.0, None)
    for t in B['tracks']:
        if t['layer'] == layer and t['net'] != skip_net:
            d = seg_pt(t['x1'], t['y1'], t['x2'], t['y2'], x, y) - t['w'] / 2
            if d < best[0]:
                best = (d, 'track %s %s (%.3f,%.3f)-(%.3f,%.3f) w%.3f' % (t['net'], layer, t['x1'], t['y1'], t['x2'], t['y2'], t['w']))
    for v in B['vias']:
        if layer in v['span'] and v['net'] != skip_net:
            d = math.hypot(v['x'] - x, v['y'] - y) - v['size'] / 2
            if d < best[0]:
                best = (d, 'via %s (%.3f,%.3f) %.2f/%.2f %s' % (v['net'], v['x'], v['y'], v['size'], v['hole'], '>'.join((v['span'][0], v['span'][-1]))))
    for p in B['pads']:
        if p['net'] != skip_net and (p['layer'] == layer or p['layer'] == 'Multi'):
            a = math.radians(-p['rot'])
            dx, dy = x - p['x'], y - p['y']
            lx, ly = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
            d = math.hypot(max(abs(lx) - p['size_x'] / 2, 0), max(abs(ly) - p['size_y'] / 2, 0))
            if d < best[0]:
                best = (d, 'pad %s-%s (%s) at (%.3f,%.3f)' % (p['ref'], p['pad'], p['net'], p['x'], p['y']))
    return r4(best[0]), best[1]


def local_room(B, esc, rasters, body):
    """for each DQ: (a) on Bottom, the clear run straight outward from the pad's outer edge (away from the U3 body) in
    the pad's own column (pad width), measured geometrically: distance until any OTHER-net Bottom copper edge comes
    within 0.09 mm (Clearance rule) of the column, and until another part's body proxy comes within 0.254 mm
    (ComponentClearance) -- U3 itself and X2 excluded; (b) at the first via, the nearest other-net copper on Top and
    on Bottom, and which Top part body sits over the via."""
    out = {}
    for net, e in esc.items():
        p = e['u3_pad']
        south = p['y'] < 12
        sgn = -1 if south else 1
        y_edge = p['y'] + sgn * p['h'] / 2
        xa, xb = p['x'] - p['w'] / 2, p['x'] + p['w'] / 2
        y_far = 0.0 if south else 25.4
        ylo, yhi = min(y_edge, y_far), max(y_edge, y_far)
        # other-net Bottom copper inside the column's corridor (inflated by the gap): first hit distance from the pad edge
        hits = []

        def note(y0, y1, what):
            # an obstacle occupying y0..y1 (already inflated) that overlaps the column in x
            if y1 < ylo or y0 > yhi:
                return
            dd = (y_edge - y1) if south else (y0 - y_edge)
            hits.append((max(dd, 0.0), what))
        g = CU_GAP
        for t in B['tracks']:
            if t['layer'] != 'Bottom' or t['net'] == net or t['polygon'] != 65535:
                continue
            hw = t['w'] / 2 + g
            # sample the segment finely; keep points whose capsule overlaps the column
            n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.02))
            for k in range(n + 1):
                x = t['x1'] + (t['x2'] - t['x1']) * k / n
                y = t['y1'] + (t['y2'] - t['y1']) * k / n
                if x + hw >= xa and x - hw <= xb:
                    note(y - hw, y + hw, 'track %s (%.3f,%.3f)-(%.3f,%.3f) w%.3f' % (t['net'], t['x1'], t['y1'], t['x2'], t['y2'], t['w']))
        for v in B['vias']:
            if 'Bottom' in v['span'] and v['net'] != net:
                r = v['size'] / 2 + g
                if v['x'] + r >= xa and v['x'] - r <= xb:
                    note(v['y'] - r, v['y'] + r, 'via %s (%.3f,%.3f) %.2f %s' % (v['net'], v['x'], v['y'], v['size'], '>'.join((v['span'][0], v['span'][-1]))))
        for q in B['pads']:
            if q['layer'] in ('Bottom', 'Multi') and q['net'] != net and not (q['ref'] == 'U3' and q['pad'] == p['pad']):
                if q['x'] + q['w'] / 2 + g >= xa and q['x'] - q['w'] / 2 - g <= xb:
                    note(q['y'] - q['h'] / 2 - g, q['y'] + q['h'] / 2 + g, 'pad %s-%s (%s) at (%.3f,%.3f)' % (q['ref'], q['pad'], q['net'], q['x'], q['y']))
        cu = min(hits) if hits else (r4(abs(y_far - y_edge)), 'board edge')
        parts = []
        for c in rasters['Bottom']['plist']:
            if c['ref'] in ('U3', 'X2'):
                continue
            x0, y0, x1, y1 = c['box']
            if x1 + COMP_GAP >= xa and x0 - COMP_GAP <= xb:
                a, b = y0 - COMP_GAP, y1 + COMP_GAP
                if not (b < ylo or a > yhi):
                    parts.append((max((y_edge - b) if south else (a - y_edge), 0.0), '%s %s body %s' % (c['ref'], c['footprint'], c['box'])))
        pt = min(parts) if parts else (r4(abs(y_far - y_edge)), 'board edge')
        fv = e['first_via']
        nb = body['body']['nom']
        out[net] = dict(
            pad=p, outward='-y (south, toward board edge y=0)' if south else '+y (north, toward board edge y=25.4)',
            pad_outer_edge_y=r4(y_edge),
            bottom_outward_clear_run_copper=[r4(cu[0]), cu[1]],
            bottom_outward_clear_run_part_body=[r4(pt[0]), pt[1]],
            first_via=[fv['x'], fv['y']],
            first_via_centre_inside_u3_nominal_body_by=r4(min(fv['y'] - nb['y0'], nb['y1'] - fv['y'], fv['x'] - nb['x0'], nb['x1'] - fv['x'])),
            first_via_nearest_other_copper_Top=copper_dist(B, 'Top', fv['x'], fv['y'], net),
            first_via_nearest_other_copper_Bottom=copper_dist(B, 'Bottom', fv['x'], fv['y'], net),
            top_parts_over_first_via=[c['ref'] for c in rasters['Top']['plist'] if c['ref'] != 'X2' and
                                      c['box'][0] <= fv['x'] <= c['box'][2] and c['box'][1] <= fv['y'] <= c['box'][3]],
        )
    return out


def model_diff(B):
    """whole-board difference between tools/route/model.json and this PcbDoc read (copper only, 2 um tolerance)"""
    if not os.path.exists(MODEL):
        return None
    M = json.load(open(MODEL))

    def kt(L, w, a, b, n):
        return (L, n or '', round(w, 3), tuple(sorted([(round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))])))
    mt = {kt(MODEL_LAYER[t['layer']], t['w'], (t['x1'], t['y1']), (t['x2'], t['y2']), t['net']) for t in M['tracks']}
    bt = {kt(t['layer'], t['w'], (t['x1'], t['y1']), (t['x2'], t['y2']), t['net']) for t in B['tracks']
          if t['layer'] in COPPER and t['polygon'] == 65535}
    mv = {(round(v['x'], 3), round(v['y'], 3), v['net'] or '', tuple(MODEL_LAYER[s] for s in v['span'])) for v in M['vias']}
    bv = {(round(v['x'], 3), round(v['y'], 3), v['net'] or '', tuple(v['span'])) for v in B['vias']}
    mp = {(p['ref'], p['pad'], round(p['x'], 3), round(p['y'], 3), p['net'] or '') for p in M['pads']}
    bp = {(p['ref'], p['pad'], round(p['x'], 3), round(p['y'], 3), p['net'] or '') for p in B['pads'] if p['ref']}

    def flat(t):
        for v in t:
            if isinstance(v, tuple):
                yield from flat(v)
            else:
                yield v

    def same(x, y):
        fx, fy = list(flat(x)), list(flat(y))
        return len(fx) == len(fy) and all((abs(p - q) <= 0.002) if isinstance(p, float) and isinstance(q, float) else p == q
                                          for p, q in zip(fx, fy))

    def fuzzy(a, b):
        rest = list(b - a)
        return [x for x in a - b if not any(same(x, y) for y in rest)]
    ot, nt = fuzzy(mt, bt), fuzzy(bt, mt)
    ov, nv = fuzzy(mv, bv), fuzzy(bv, mv)
    op, np_ = fuzzy(mp, bp), fuzzy(bp, mp)
    allt = ot + nt
    raw_b = sum(1 for t in B['tracks'] if t['layer'] in COPPER and t['polygon'] == 65535)
    return dict(note='counts below are unique keys; raw copper track records: model %d, PcbDoc %d' % (len(M['tracks']), raw_b),
                model_counts=dict(pads=len(M['pads']), tracks=len(mt), vias=len(mv)),
                pcbdoc_counts=dict(pads=len(bp), tracks=len(bt), vias=len(bv)),
                tracks_only_in_model=len(ot), tracks_only_in_pcbdoc=len(nt), vias_only_in_model=ov, vias_only_in_pcbdoc=nv,
                pads_only_in_model=op, pads_only_in_pcbdoc=np_,
                nets_of_changed_tracks=sorted({x[1] for x in allt}),
                changed_track_bbox=[r4(min(min(x[3][0][0], x[3][1][0]) for x in allt)), r4(min(min(x[3][0][1], x[3][1][1]) for x in allt)),
                                    r4(max(max(x[3][0][0], x[3][1][0]) for x in allt)), r4(max(max(x[3][0][1], x[3][1][1]) for x in allt))] if allt else None,
                any_D_net_touched=any(n in DNETS for n in {x[1] for x in allt} | {x[2] for x in ov + nv} | {x[4] for x in op + np_}))


# ------------------------------------------------------------------------------------------- render
def render(B, rasters, body, esc, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Rectangle, Circle, Polygon as MPoly
    from matplotlib.lines import Line2D

    def capsule(ax, x1, y1, x2, y2, w, **kw):
        L = math.hypot(x2 - x1, y2 - y1)
        hw = w / 2
        if L > 1e-9:
            nx, ny = -(y2 - y1) / L * hw, (x2 - x1) / L * hw
            ax.add_patch(MPoly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], closed=True, **kw))
        ax.add_patch(Circle((x1, y1), hw, **kw))
        ax.add_patch(Circle((x2, y2), hw, **kw))

    fig, axes = plt.subplots(1, 2, figsize=(24, 13.5), dpi=120)
    for ax, side in zip(axes, ('Top', 'Bottom')):
        R = rasters[side]
        ax.set_facecolor('white')
        cu_free = R['dist'] > CU_GAP
        place = cu_free & ~R['parts']
        shade = np.where(place, 2.0, np.where(cu_free, 1.0, np.nan))
        ax.imshow(shade, extent=(WIN['x0'], WIN['x1'], WIN['y0'], WIN['y1']), origin='lower', cmap='Greens', vmin=0, vmax=3.2,
                  alpha=0.5, interpolation='nearest', zorder=0)
        other = 'Bottom' if side == 'Top' else 'Top'
        own = '#c0392b' if side == 'Top' else '#2c6fbb'
        for t in B['tracks']:
            if t['polygon'] != 65535:
                continue
            isd = t['net'] in DNETS
            if t['layer'] == side:
                capsule(ax, t['x1'], t['y1'], t['x2'], t['y2'], t['w'], fc='#ff7f0e' if isd else own, ec='none',
                        alpha=1.0 if isd else 0.75, zorder=4 if isd else 2)
            elif isd and t['layer'] in ('L3-SIG', 'L4-SIG', other):
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='#ff7f0e', lw=0.7, ls=':', alpha=0.8, zorder=3)
        for p in B['pads']:
            if p['layer'] in (side, 'Multi') and WIN['x0'] - 2 < p['x'] < WIN['x1'] + 2:
                isd = p['net'] in DNETS
                fc = '#ff7f0e' if isd else ('#8c564b' if p['layer'] == 'Multi' else own)
                if p['shape'] == 'round':
                    ax.add_patch(Circle((p['x'], p['y']), min(p['size_x'], p['size_y']) / 2, fc=fc, ec='k', lw=0.2, zorder=5))
                else:
                    a = math.radians(p['rot'])
                    hx, hy = p['size_x'] / 2, p['size_y'] / 2
                    pts = [(p['x'] + px * math.cos(a) - py * math.sin(a), p['y'] + px * math.sin(a) + py * math.cos(a))
                           for px, py in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
                    ax.add_patch(MPoly(pts, closed=True, fc=fc, ec='k', lw=0.2, zorder=5))
                if isd and p['ref'] == 'U3':
                    ax.text(p['x'], p['y'] + (-0.95 if p['y'] < 12 else 0.95), p['net'], fontsize=6.5, ha='center', va='center',
                            color='#a04000', rotation=90, zorder=11)
        for v in B['vias']:
            if side in v['span'] and WIN['x0'] - 1 < v['x'] < WIN['x1'] + 1:
                isd = v['net'] in DNETS
                ec = '#ff7f0e' if isd else ('k' if v['kind'] == 'through' else '#9467bd')
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='#ffd27f' if isd else '#d9d9d9', ec=ec, lw=0.6 if isd else 0.3, zorder=6))
                ax.add_patch(Circle((v['x'], v['y']), v['hole'] / 2, fc='white', ec='none', zorder=7))
        for c in R['plist']:
            if c['ref'] == 'X2':
                continue
            x0, y0, x1, y1 = c['box']
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec='#444444', lw=0.7, ls='--', zorder=8))
            if WIN['x0'] < (x0 + x1) / 2 < WIN['x1'] and c['ref'] != 'U3':
                ax.text((x0 + x1) / 2, y1 + 0.12, c['ref'], fontsize=6, ha='center', va='bottom', color='#222222', zorder=9, clip_on=True)
        for t in B['texts']:
            if t['layer'] == (side + 'Overlay') and not t['hidden'] and WIN['x0'] <= t['x'] < WIN['x1'] and WIN['y0'] <= t['y'] < WIN['y1']:
                ax.text(t['x'], t['y'], t['text'], fontsize=5.5, color='#9a7d00', ha='left', va='bottom', zorder=9,
                        rotation=t['rot'], clip_on=True)
        if side == 'Bottom':
            for k, ls in (('nom', '-'), ('max', '--')):
                bb = body['body'][k]
                ax.add_patch(Rectangle((bb['x0'], bb['y0']), bb['x1'] - bb['x0'], bb['y1'] - bb['y0'], fill=False,
                                       ec='#1a7f1a', lw=1.3, ls=ls, zorder=10))
            for t in B['tracks']:
                if t['comp'] == 'U3' and t['layer'] == 'Mech8':
                    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='#7b3294', lw=0.9, ls='-.', zorder=10)
            ax.text(body['body']['nom']['x1'] - 0.2, 11.85, 'U3 TSOP-II 54 (Bottom)\nbody: datasheet nom (solid) / max (dashed)\n'
                    'purple dash-dot = footprint Mech8 outline', color='#1a7f1a', fontsize=7.5, ha='right', va='center', zorder=10)
        for net, e in esc.items():
            fv = e['first_via']
            ax.text(fv['x'], fv['y'] + (0.32 if fv['y'] > 12 else -0.32), net, fontsize=6, color='#a04000', ha='center',
                    va='center', zorder=11)
        ax.set_xlim(WIN['x0'], WIN['x1'])
        ax.set_ylim(WIN['y0'], WIN['y1'])
        ax.set_aspect('equal')
        ax.set_xticks(np.arange(25, 50.01, 1), minor=True)
        ax.set_xticks(np.arange(25, 50.01, 5))
        ax.set_yticks(np.arange(0, 25.41, 1), minor=True)
        ax.grid(True, which='both', lw=0.25, color='#c8c8c8', zorder=1)
        ax.set_title('%s layer, seen from above (x 25..50, y 0..25.4 mm)' % side, fontsize=11)
        ax.set_xlabel('x mm (board origin bottom-left)')
        ax.set_ylabel('y mm')
    handles = [Line2D([], [], color='#ff7f0e', lw=4, label='D0-D15 copper on this layer (pads, tracks, vias)'),
               Line2D([], [], color='#ff7f0e', lw=1, ls=':', label='D0-D15 on L3/L4 or the other outer layer'),
               Line2D([], [], color='#c0392b', lw=4, label='other Top copper'),
               Line2D([], [], color='#2c6fbb', lw=4, label='other Bottom copper'),
               Line2D([], [], color='#8c564b', lw=4, label='through-hole pads'),
               Line2D([], [], marker='o', color='k', mfc='#d9d9d9', ls='', label='through via (0.35/0.20)'),
               Line2D([], [], marker='o', color='#9467bd', mfc='#d9d9d9', ls='', label='microvia / laser via'),
               Line2D([], [], color='#444444', lw=1, ls='--', label='part body proxy (pads + Mech3/4 drawing)'),
               Rectangle((0, 0), 1, 1, fc='#74c476', alpha=0.6, label='placement room: no copper within 0.09 mm, >= 0.254 mm from bodies'),
               Rectangle((0, 0), 1, 1, fc='#c7e9c0', alpha=0.6, label='copper-free (0.09 mm) but inside a body keep-off: routing room only')]
    fig.legend(handles=handles, loc='lower center', ncol=5, fontsize=8.5, frameon=False)
    fig.suptitle('Zulu_a7_no_pmod Rev 2 -- U3 DQ escape region (read from the saved PcbDoc, %s)' % os.path.basename(PCB), fontsize=12)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(path)
    plt.close(fig)


# ------------------------------------------------------------------------------------------- main
def main():
    import numpy as np
    B = read_pcbdoc(PCB)
    st = os.stat(PCB)
    import hashlib
    md5 = hashlib.md5(open(PCB, 'rb').read()).hexdigest()
    lib = read_pcblib(LIB)
    outl = comp_outlines(B)
    body = u3_body(B)
    esc = escapes(B)
    xc = crosscheck(B)
    rules = rules_out(B)

    rasters = {s: raster(B, s, outl, body) for s in ('Top', 'Bottom')}
    # zones: within 5 mm of either DQ pad row (x extent of D pads +-5) and of the D escape vias
    dpads = [p for p in B['pads'] if p['ref'] == 'U3' and p['net'] in DNETS]
    dvias = [e['first_via'] for e in esc.values() if e['first_via']]
    free_out = {}
    for side in ('Top', 'Bottom'):
        R = rasters[side]
        X, Y = R['X'], R['Y']
        for rowname, ps, vs in (('south_D0-D7', [p for p in dpads if p['y'] < 12], [v for v in dvias if v['y'] < 12]),
                                ('north_D8-D15', [p for p in dpads if p['y'] > 12], [v for v in dvias if v['y'] > 12])):
            pts = [(p['x'], p['y']) for p in ps] + [(v['x'], v['y']) for v in vs]
            zx0, zx1 = min(q[0] for q in pts) - 5, max(q[0] for q in pts) + 5
            zy0, zy1 = min(q[1] for q in pts) - 5, max(q[1] for q in pts) + 5
            zone = (X >= zx0) & (X <= zx1) & (Y >= zy0) & (Y <= zy1) & (X >= 0.25) & (Y >= 0.25) & (Y <= 25.15)
            res = {}
            for label, clr, bodies in (('placement: no copper within 0.09, >= 0.254 from part bodies', CU_GAP, 'body'),
                                       ('copper-only: no copper within 0.09 (part bodies ignored -- routing room, not placement room)', CU_GAP, None)):
                free = R['dist'] > clr
                if bodies == 'body':
                    free &= ~R['parts']
                res[label] = dict(free_mm2=r4(float((free & zone).sum()) * GRID * GRID),
                                  rects=max_rects(free, X, Y, min_w=0.30, min_h=0.30, n=25, zone=zone))
            # obstacles in the zone
            obs = dict(
                pads=sorted({'%s-%s(%s)' % (p['ref'], p['pad'], p['net']) for p in B['pads']
                             if p['layer'] in (side, 'Multi') and zx0 <= p['x'] <= zx1 and zy0 <= p['y'] <= zy1}),
                parts=[c for c in R['plist'] if c['box'][2] >= zx0 and c['box'][0] <= zx1 and c['box'][3] >= zy0 and c['box'][1] <= zy1],
                vias=len([v for v in B['vias'] if side in v['span'] and zx0 <= v['x'] <= zx1 and zy0 <= v['y'] <= zy1]),
                via_nets=sorted({v['net'] or '' for v in B['vias'] if side in v['span'] and zx0 <= v['x'] <= zx1 and zy0 <= v['y'] <= zy1}),
                tracks=len([t for t in B['tracks'] if t['layer'] == side and t['polygon'] == 65535 and
                            (zx0 <= t['x1'] <= zx1 and zy0 <= t['y1'] <= zy1 or zx0 <= t['x2'] <= zx1 and zy0 <= t['y2'] <= zy1)]),
                track_nets=sorted({t['net'] or '' for t in B['tracks'] if t['layer'] == side and t['polygon'] == 65535 and
                                   (zx0 <= t['x1'] <= zx1 and zy0 <= t['y1'] <= zy1 or zx0 <= t['x2'] <= zx1 and zy0 <= t['y2'] <= zy1)}),
                keepouts=[dict(kind=k, layer=o['layer']) for k, lst in (('track', B['tracks']), ('arc', B['arcs']))
                          for o in lst if (o['keepout'] or o['layer'] == 'KeepOut')] +
                         [dict(kind='region', layer=r['layer'], pts=r['pts']) for r in B['regions'] + B['sregions'] if r['keepout'] or r['layer'] == 'KeepOut'],
                silk_texts=[t for t in B['texts'] if t['layer'] == ('TopOverlay' if side == 'Top' else 'BottomOverlay')
                            and zx0 - 3 <= t['x'] <= zx1 and zy0 - 3 <= t['y'] <= zy1 and not t['hidden']],
            )
            free_out['%s/%s' % (side, rowname)] = dict(zone=[r4(zx0), r4(zy0), r4(zx1), r4(zy1)], free=res, obstacles=obs)

    # regions: keep Top/Bottom/non-copper ones in full, summarise the L2/L5 pours
    def keep(r):
        return r['layer'] not in ('L2-GND', 'L5-VCC3V3', 'L3-SIG', 'L4-SIG')
    pour_summary = defaultdict(lambda: dict(count=0, net=set()))
    for r in B['regions']:
        if not keep(r):
            s = pour_summary[r['layer']]
            s['count'] += 1
            s['net'].add(r['net'] or '')
    pour_summary = {k: dict(count=v['count'], nets=sorted(v['net'])) for k, v in pour_summary.items()}

    out = dict(
        source=dict(pcbdoc=PCB, pcbdoc_mtime=st.st_mtime, pcbdoc_md5=md5, pcblib=LIB, script=HERE + '/extract.py',
                    units='mm, board origin bottom-left (Board6 ORIGINX/Y = 0), y up',
                    board_outline=[[r4(mil(B['board'].get('VX%d' % k))), r4(mil(B['board'].get('VY%d' % k)))]
                                   for k in range(10) if 'VX%d' % k in B['board']],
                    body_source=('PcbDoc ComponentBodies6 and ShapeBasedComponentBodies6 are EMPTY (0 bytes) and the project '
                                 'PcbLib has no TSOPII-54 footprint (it holds %s) -- so component outlines here are the PcbDoc '
                                 'primitives each component owns (pads + overlay/mech per layer); U3 body is the datasheet '
                                 'outline centred on the measured pad field' % sorted(lib))),
        counts=dict(components=len(B['comps']), pads=len(B['pads']), tracks=len(B['tracks']), arcs=len(B['arcs']),
                    vias=len(B['vias']), fills=len(B['fills']), regions=len(B['regions']), shape_regions=len(B['sregions']),
                    texts=len(B['texts']), polygons=len(B['polygons'])),
        components=B['comps'],
        component_outlines=outl,
        pcblib=lib,
        u3=body,
        pads=B['pads'],
        tracks=[t for t in B['tracks'] if t['polygon'] == 65535 or t['layer'] in ('Top', 'Bottom')],
        polygon_tracks_omitted=sum(1 for t in B['tracks'] if t['polygon'] != 65535 and t['layer'] not in ('Top', 'Bottom')),
        arcs=B['arcs'],
        vias=B['vias'],
        fills=B['fills'],
        regions=[r for r in B['regions'] if keep(r)],
        regions_note=('Regions6 and ShapeBasedRegions6 each hold %d records on the same layers/owners (the shape-based '
                      'copy repeats the closing vertex); only Regions6 is listed' % len(B['regions'])),
        inner_pour_regions_summary=pour_summary,
        polygons=B['polygons'],
        texts=B['texts'],
        rules=rules,
        rules_summary=rules_summary(rules),
        net_classes={kv['NAME']: [v for k, v in kv.items() if k[:1] == 'M' and k[1:].isdigit()] for kv in B['classes']
                     if kv.get('KIND') == '0' and kv.get('NAME') in ('SDRAM_DATA', 'SDRAM_ADDR', 'SDRAM_CTRL', 'PWR_RAILS', 'PWR_SWITCH')},
        d_escapes=esc,
        dq_local_room=local_room(B, esc, rasters, body),
        model_json_whole_board_diff=model_diff(B),
        free_area=free_out,
        model_json_crosscheck=xc,
    )
    json.dump(out, open(OUT, 'w'), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    render(B, rasters, body, esc, PNG)
    print('wrote', OUT, 'and', PNG)
    print('counts', out['counts'])


if __name__ == '__main__':
    main()
