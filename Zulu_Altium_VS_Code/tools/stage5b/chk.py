# -*- coding: utf-8 -*-
"""Exact legality of one 0201 stitching site: tools/block_place.py's placement conventions,
tools/route_emit.py's via and track rules, stitch_brief.md's extra via rules, and -- the part no
shipped gate can see -- the TRUE moulded-body boxes fitted from the EAGLE packages (bodies.py).

A site is (x, y, layer, axis).  Geometry: pads 0.30x0.30 at +-0.30 along the axis; both vias on the
same side of the part, each OFF mm off the axis at its own pad's along-coordinate, so the via-to-via
loop is the 0.5999 mm land pitch and each via land clears its own land by OFF-0.325.
"""
import io, json, math, os, sys
REPO = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium'
sys.path.insert(0, os.path.join(REPO, 'tools'))
from route_emit import seg_rect, seg_dist
import bodies

INP = json.load(io.open(os.path.join(REPO, 'tools', 'route_inputs.json'), encoding='utf-8'))
OL, EPS = INP['outline'], 1e-9
LAND_CLEAR, EDGE_PAD, C = 0.30, 0.30, 0.09
VIA_LAND, VIA_PITCH = 0.35, 0.44
VIA_EDGE_IN = 0.80
LANDF = (41.7875, 7.2875, 51.0125, 16.5125)
PAD, PITCH = 0.30, 0.60
ENV = (1.00, 0.60)
OFF = 0.425
SDRAM = {n for n, v in INP['nets'].items() if (v.get('cls') or '').startswith('SDRAM')}


def pt_rect(px, py, cx, cy, sx, sy):
    return math.hypot(max(abs(px - cx) - sx / 2, 0.0), max(abs(py - cy) - sy / 2, 0.0))


def rect_gap(ax, ay, asx, asy, bx, by, bsx, bsy):
    return math.hypot(max(abs(ax - bx) - (asx + bsx) / 2, 0.0), max(abs(ay - by) - (asy + bsy) / 2, 0.0))


def gap_for(net, layer):
    if layer in ('L3-SIG', 'L4-SIG'):
        if net == 'SDRAM-CLK':
            return 0.20
        if net in SDRAM:
            return 0.10
    return C


def _part_boxes():
    """per side, exactly what each test needs.

    PEX[side][ref] -- the pad-extent box, for parts with SMD pads on that side.  This is
        tools/block_place.py's courtyard-lite box, reproduced exactly (block_place indexes
        bottom_pads, so a through-hole-only part such as X2 has no box and is tested only by
        the 0.30 mm land-gap rule; the same applies here).
    BODY[side][ref] -- the EAGLE layer-21 outline fitted to the part's own pads, for parts with
        MORE THAN TWO pads, i.e. the real moulded body of an IC or a connector.  For a two-pad chip
        the layer-21 rectangle is the silk courtyard, not a body, so it is left out.
    KEEP[side][ref] -- the layer-39 keep-out box on the same terms; advisory, reported not enforced.
    """
    B = bodies.board_bodies()
    ext, npad, side = {}, {}, {}
    smdside = {}

    def add(p, L):
        e = ext.setdefault(p['ref'], [9e9, 9e9, -9e9, -9e9])
        e[0] = min(e[0], p['x'] - p['sx'] / 2)
        e[1] = min(e[1], p['y'] - p['sy'] / 2)
        e[2] = max(e[2], p['x'] + p['sx'] / 2)
        e[3] = max(e[3], p['y'] + p['sy'] / 2)
        npad[p['ref']] = npad.get(p['ref'], 0) + 1
        if L:
            smdside[p['ref']] = L
    for p in INP['top_pads']:
        add(p, 'Top')
    for p in INP['bottom_pads']:
        add(p, 'Bottom')
    for p in INP['th_pads']:
        add(p, None)
    pex = {'Top': {}, 'Bottom': {}}
    body = {'Top': {}, 'Bottom': {}}
    keep = {'Top': {}, 'Bottom': {}}
    for r, e in ext.items():
        s = smdside.get(r)
        if s is None:
            continue
        pex[s][r] = tuple(e)
        if npad[r] > 2 and r in B:
            q = B[r]['boxes'].get('21')
            if q:
                body[s][r] = q
            q = B[r]['boxes'].get('39')
            if q:
                keep[s][r] = q
    return pex, body, keep


PEX, BODY, KEEP = _part_boxes()


def boxes_of(x, y, axis):
    pw, ph = (0.45, 0.15) if axis == 'H' else (0.15, 0.45)
    ew, eh = (ENV[0] / 2, ENV[1] / 2) if axis == 'H' else (ENV[1] / 2, ENV[0] / 2)
    return (x - pw, y - ph, x + pw, y + ph), (x - ew, y - eh, x + ew, y + eh)


def overlap(a, b):
    return (min(a[2], b[2]) - max(a[0], b[0]) > EPS) and (min(a[3], b[3]) - max(a[1], b[1]) > EPS)


def geom(x, y, axis, side=+1, off=OFF):
    """pad centres and via centres; pad 1 (VCC3V3) is the west/south pad, via i serves pad i."""
    if axis == 'H':
        pads = [(x - PITCH / 2, y), (x + PITCH / 2, y)]
        vias = [(x - PITCH / 2, y + side * off), (x + PITCH / 2, y + side * off)]
    else:
        pads = [(x, y - PITCH / 2), (x, y + PITCH / 2)]
        vias = [(x + side * off, y - PITCH / 2), (x + side * off, y + PITCH / 2)]
    return pads, vias


def check(x, y, layer, axis, side=+1, others=(), stub_w=0.30, off=OFF, vias=None):
    """others: sister sites [(x, y, layer, axis, vias)] so a whole plan is checked against itself.
    vias: an explicit [(vx,vy) for VCC3V3, (vx,vy) for GND]; omitted means the symmetric pair."""
    bad = []
    pads, gvias = geom(x, y, axis, side, off)
    vias = [tuple(v) for v in vias] if vias else gvias
    key = 'top_pads' if layer == 'Top' else 'bottom_pads'
    pex, env = boxes_of(x, y, axis)
    for i, (cx, cy) in enumerate(pads):
        if min(cx - PAD / 2 - OL['x0'], OL['x1'] - cx - PAD / 2,
               cy - PAD / 2 - OL['y0'], OL['y1'] - cy - PAD / 2) < EDGE_PAD - EPS:
            bad.append('pad %d under %.2f mm from the board edge' % (i + 1, EDGE_PAD))
        for p in INP[key]:
            g = rect_gap(cx, cy, PAD, PAD, p['x'], p['y'], p['sx'], p['sy'])
            if g < LAND_CLEAR - EPS:
                bad.append('pad %d land gap %.4f to %s-%s (min %.2f)' % (i + 1, g, p['ref'], p['pad'], LAND_CLEAR))
        for p in INP['th_pads']:
            g = rect_gap(cx, cy, PAD, PAD, p['x'], p['y'], p['sx'], p['sy'])
            if g < LAND_CLEAR - EPS:
                bad.append('pad %d land gap %.4f to TH %s-%s' % (i + 1, g, p['ref'], p['pad']))
        for t in INP['tracks']:
            if t['layer'] != layer:
                continue
            g = seg_rect((t['x1'], t['y1'], t['x2'], t['y2']), cx, cy, PAD, PAD) - t['width'] / 2
            if g < C - EPS:
                bad.append('pad %d %.4f from a %s %s track' % (i + 1, g, layer, t['net']))
        for v in INP['vias']:
            g = pt_rect(v['x'], v['y'], cx, cy, PAD, PAD) - v['size'] / 2
            if g < C - EPS:
                bad.append('pad %d %.4f from a %s via' % (i + 1, g, v['net']))
        for k in INP.get('keepouts', []):
            if k.get('layer') != layer:
                continue
            g = rect_gap(cx, cy, PAD, PAD, (k['x0'] + k['x1']) / 2, (k['y0'] + k['y1']) / 2,
                         k['x1'] - k['x0'], k['y1'] - k['y0'])
            if g < C - EPS:
                bad.append('pad %d inside the %s keep-out' % (i + 1, k['layer']))
    for r, b in PEX[layer].items():
        if overlap(pex, b):
            bad.append('pad-extent box overlaps %s' % r)
    for r, b in BODY[layer].items():
        if overlap(env, b):
            bad.append('1.00x0.60 envelope overlaps the %s MOULDED BODY (%.3f,%.3f)-(%.3f,%.3f)' % ((r,) + tuple(b)))
    for (ox, oy, olay, oax, ovias) in others:
        op = geom(ox, oy, oax)[0]
        ov = [tuple(v) for v in ovias]
        opex, oenv = boxes_of(ox, oy, oax)
        if olay == layer:
            if overlap(pex, opex):
                bad.append('pad-extent box overlaps a sister part at %.3f,%.3f' % (ox, oy))
            for (cx, cy) in pads:
                for (qx, qy) in op:
                    g = rect_gap(cx, cy, PAD, PAD, qx, qy, PAD, PAD)
                    if g < LAND_CLEAR - EPS:
                        bad.append('land gap %.4f to a sister land' % g)
        for (vx, vy) in vias:
            for (qx, qy) in ov:
                d = math.hypot(vx - qx, vy - qy)
                if d < VIA_PITCH - EPS:
                    bad.append('via pitch %.4f to a sister via' % d)
            for (qx, qy) in op:
                d = pt_rect(vx, vy, qx, qy, PAD, PAD) - VIA_LAND / 2
                if d < C - EPS:
                    bad.append('via %.4f from a sister land' % d)
    r = VIA_LAND / 2
    for i, (vx, vy) in enumerate(vias):
        net = 'VCC3V3' if i == 0 else 'GND'
        if LANDF[0] - r <= vx <= LANDF[2] + r and LANDF[1] - r <= vy <= LANDF[3] + r:
            bad.append('via %d inside U1 land field' % (i + 1))
        if min(vx - OL['x0'], OL['x1'] - vx, vy - OL['y0'], OL['y1'] - vy) < VIA_EDGE_IN - EPS:
            bad.append('via %d land under 0.80 mm inside the outline' % (i + 1))
        for v in INP['vias']:
            d = math.hypot(vx - v['x'], vy - v['y'])
            if d < VIA_PITCH - EPS:
                bad.append('via %d pitch %.4f to a %s via' % (i + 1, d, v['net']))
        for j, (qx, qy) in enumerate(vias):
            if j != i and math.hypot(vx - qx, vy - qy) < VIA_PITCH - EPS:
                bad.append('via %d pitch %.4f to its partner' % (i + 1, math.hypot(vx - qx, vy - qy)))
        for p in INP['top_pads'] + INP['bottom_pads']:
            d = pt_rect(vx, vy, p['x'], p['y'], p['sx'], p['sy']) - r
            if d < C - EPS:
                bad.append('via %d %.4f from pad %s-%s' % (i + 1, d, p['ref'], p['pad']))
        for (cx, cy) in pads:
            d = pt_rect(vx, vy, cx, cy, PAD, PAD) - r
            if d < C - EPS:
                bad.append('via %d %.4f from its own land' % (i + 1, d))
        for p in INP['th_pads']:
            d = pt_rect(vx, vy, p['x'], p['y'], p['sx'], p['sy']) - r
            if d < 0.10 - EPS:
                bad.append('via %d %.4f from TH %s-%s' % (i + 1, d, p['ref'], p['pad']))
        for k in INP.get('keepouts', []):
            d = pt_rect(vx, vy, (k['x0'] + k['x1']) / 2, (k['y0'] + k['y1']) / 2,
                        k['x1'] - k['x0'], k['y1'] - k['y0']) - r
            if d < C - EPS:
                bad.append('via %d %.4f from the %s keep-out' % (i + 1, d, k['layer']))
        for t in INP['tracks']:
            if t['net'] == net:
                continue
            d = seg_dist((t['x1'], t['y1'], t['x2'], t['y2']), (vx, vy, vx, vy)) - t['width'] / 2 - r
            if d < gap_for(t['net'], t['layer']) - EPS:
                bad.append('via %d %.4f from a %s %s track (rule %.2f)' % (
                    i + 1, d, t['layer'], t['net'], gap_for(t['net'], t['layer'])))
    for i, ((cx, cy), (vx, vy)) in enumerate(zip(pads, vias)):
        net = 'VCC3V3' if i == 0 else 'GND'
        seg = (cx, cy, vx, vy)
        hw = stub_w / 2
        for t in INP['tracks']:
            if t['layer'] != layer or t['net'] == net:
                continue
            d = seg_dist(seg, (t['x1'], t['y1'], t['x2'], t['y2'])) - hw - t['width'] / 2
            if d < gap_for(t['net'], layer) - EPS:
                bad.append('stub %d %.4f from a %s track (w %.3f)' % (i + 1, d, t['net'], stub_w))
        for v in INP['vias']:
            if v['net'] == net:
                continue
            d = seg_dist(seg, (v['x'], v['y'], v['x'], v['y'])) - hw - v['size'] / 2
            if d < C - EPS:
                bad.append('stub %d %.4f from a %s via' % (i + 1, d, v['net']))
        for p in INP[key] + INP['th_pads']:
            if p['net'] == net:
                continue
            d = seg_rect(seg, p['x'], p['y'], p['sx'], p['sy']) - hw
            if d < C - EPS:
                bad.append('stub %d %.4f from pad %s-%s (%s)' % (i + 1, d, p['ref'], p['pad'], p['net']))
        for j, (qx, qy) in enumerate(vias):
            if j == i:
                continue
            d = seg_dist(seg, (qx, qy, qx, qy)) - hw - r
            if d < C - EPS:
                bad.append('stub %d %.4f from its partner via' % (i + 1, d))
        for j, (qx, qy) in enumerate(pads):
            if j == i:
                continue
            d = seg_rect(seg, qx, qy, PAD, PAD) - hw
            if d < C - EPS:
                bad.append('stub %d %.4f from the other land' % (i + 1, d))
    return bad
