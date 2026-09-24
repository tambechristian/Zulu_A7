# -*- coding: utf-8 -*-
"""True component-body boxes, by fitting every EAGLE package in zulu_a7.sch to the board's own pads.

Why: tools/block_place.py's courtyard-lite test uses the PAD-EXTENT box.  For a TSOP-II the moulded
body runs PAST the end pads along the lead rows, so the pad-extent box is not the body.  This module
fits each package to each part's measured pads (rotation + mirror + translation, least squares on the
pad pattern) and returns the layer-21 (silk body) and layer-39 (keepout) boxes in board coordinates.
"""
import io, json, math, os, re, sys
from collections import defaultdict

SCH = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/zulu_a7.sch'
RI = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/route_inputs.json'

def packages():
    s = io.open(SCH, encoding='utf-8', errors='replace').read()
    out = {}
    for m in re.finditer(r'<package name="([^"]+)"[^>]*>(.*?)</package>', s, re.S):
        name, blk = m.group(1), m.group(2)
        smd = []
        for d in (dict(re.findall(r'(\w+)="([^"]*)"', a)) for a in re.findall(r'<smd ([^/>]*)/>', blk)):
            smd.append((d['name'], float(d['x']), float(d['y']), float(d['dx']), float(d['dy']),
                        float(d.get('rot', 'R0')[1:] or 0)))
        pad = []
        for d in (dict(re.findall(r'(\w+)="([^"]*)"', a)) for a in re.findall(r'<pad ([^/>]*)/>', blk)):
            pad.append((d['name'], float(d['x']), float(d['y'])))
        box = {}
        for lay in ('21', '39', '51'):
            xs, ys = [], []
            for d in (dict(re.findall(r'(\w+)="([^"]*)"', a)) for a in re.findall(r'<wire ([^/>]*)/>', blk)):
                if d.get('layer') == lay:
                    xs += [float(d['x1']), float(d['x2'])]; ys += [float(d['y1']), float(d['y2'])]
            for d in (dict(re.findall(r'(\w+)="([^"]*)"', a)) for a in re.findall(r'<rectangle ([^/>]*)/>', blk)):
                if d.get('layer') == lay:
                    xs += [float(d['x1']), float(d['x2'])]; ys += [float(d['y1']), float(d['y2'])]
            if xs:
                box[lay] = (min(xs), min(ys), max(xs), max(ys))
        out[name] = dict(smd=smd, pad=pad, box=box)
    return out

def fit(pkg, pads):
    """pads: {padname: (x, y)} on the board.  Try the 8 orthogonal placements; return (best_rms, xf)."""
    loc = {n: (x, y) for n, x, y, dx, dy, r in pkg['smd']}
    loc.update({n: (x, y) for n, x, y in pkg['pad']})
    common = [n for n in pads if n in loc]
    if len(common) < 2:
        return None
    best = None
    for mir in (1, -1):
        for rot in (0, 90, 180, 270):
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            P = []
            for n in common:
                lx, ly = loc[n]; lx *= mir
                P.append((lx * c - ly * s, lx * s + ly * c))
            ox = sum(pads[n][0] - p[0] for n, p in zip(common, P)) / len(common)
            oy = sum(pads[n][1] - p[1] for n, p in zip(common, P)) / len(common)
            rms = math.sqrt(sum((pads[n][0] - p[0] - ox) ** 2 + (pads[n][1] - p[1] - oy) ** 2
                                for n, p in zip(common, P)) / len(common))
            if best is None or rms < best[0]:
                best = (rms, mir, rot, ox, oy)
    return best

def xf_box(b, mir, rot, ox, oy):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    xs, ys = [], []
    for lx in (b[0], b[2]):
        for ly in (b[1], b[3]):
            lx2 = lx * mir
            xs.append(lx2 * c - ly * s + ox); ys.append(lx2 * s + ly * c + oy)
    return (min(xs), min(ys), max(xs), max(ys))

def board_bodies(verbose=False):
    PK = packages()
    inp = json.load(io.open(RI, encoding='utf-8'))
    side, padmap = {}, defaultdict(dict)
    for key, L in (('top_pads', 'Top'), ('bottom_pads', 'Bottom')):
        for p in inp[key]:
            padmap[p['ref']][str(p['pad'])] = (p['x'], p['y'])
            side[p['ref']] = L
    for p in inp['th_pads']:
        padmap[p['ref']][str(p['pad'])] = (p['x'], p['y'])
        side.setdefault(p['ref'], 'Bottom')
    res = {}
    for ref, pads in padmap.items():
        cand = []
        for name, pk in PK.items():
            names = {n for n, *_ in pk['smd']} | {n for n, *_ in pk['pad']}
            if not set(pads) <= names or len(names) != len(pads):
                continue
            f = fit(pk, pads)
            if f and f[0] < 0.02:
                cand.append((f[0], name, f))
        if not cand:
            continue
        cand.sort()
        rms, name, (r, mir, rot, ox, oy) = cand[0]
        boxes = {lay: xf_box(b, mir, rot, ox, oy) for lay, b in PK[name]['box'].items()}
        px0 = min(pads[n][0] for n in pads); px1 = max(pads[n][0] for n in pads)
        res[ref] = dict(pkg=name, rms=rms, side=side[ref], boxes=boxes)
    return res

if __name__ == '__main__':
    B = board_bodies()
    inp = json.load(io.open(RI, encoding='utf-8'))
    ext = defaultdict(lambda: [9e9, 9e9, -9e9, -9e9])
    for key in ('top_pads', 'bottom_pads', 'th_pads'):
        for p in inp[key]:
            e = ext[p['ref']]
            e[0] = min(e[0], p['x'] - p['sx'] / 2); e[1] = min(e[1], p['y'] - p['sy'] / 2)
            e[2] = max(e[2], p['x'] + p['sx'] / 2); e[3] = max(e[3], p['y'] + p['sy'] / 2)
    print('%-6s %-22s %-7s %-6s  %-34s %-34s overhang beyond pad extent' % ('ref', 'package', 'side', 'rms', 'pad-extent box', 'silk-body box (layer 21)'))
    worst = []
    for ref in sorted(B):
        b = B[ref]; e = ext[ref]
        s21 = b['boxes'].get('21') or b['boxes'].get('39')
        if not s21:
            continue
        ov = max(e[0] - s21[0], e[1] - s21[1], s21[2] - e[2], s21[3] - e[3])
        worst.append((ov, ref, b, e, s21))
    worst.sort(reverse=True)
    for ov, ref, b, e, s21 in worst[:18]:
        print('%-6s %-22s %-7s %.4f  (%.3f,%.3f)-(%.3f,%.3f)  (%.3f,%.3f)-(%.3f,%.3f)  %+.4f' % (
            ref, b['pkg'], b['side'], b['rms'], e[0], e[1], e[2], e[3], s21[0], s21[1], s21[2], s21[3], ov))
    print('\nparts fitted: %d' % len(B))
