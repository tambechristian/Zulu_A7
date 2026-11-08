"""Colour the block diagram (asar_a7_0.SchDoc, sheet 1): fill the thick bus arrows and darken the labels.

The thick arrows are outlines drawn with separate sheet-level lines, closed at their base by a block's edge. This
splits every line at its crossings, traces the enclosed faces, and picks each arrow's face by a seed point: the
anchor of its label, or a point in its leg for the two unlabelled arrows (STEMMA QT and LED/Button into the FPGA).
Each picked face must have arrowhead diagonals and must not be a block. One filled Polygon record (RECORD=7) per
arrow goes in right after the block fills (fill_block_diagram.py), under every line and text that follows.
Every grey (8421504) sheet-level label becomes the new text colour. OwnerIndex values past the insertion point move
up by the number of inserted records and the header Weight follows the record count; the check after the edit
proves nothing else changed. Refuses if the sheet already has a filled polygon (runs once).

    python tools/color_block_diagram.py [--arrow 0xRRGGBB] [--text 0xRRGGBB] [--preview png] [--out path]

Close the sheet in Altium first. Defaults: light orange arrows (#FFCC99), black labels.
"""
import argparse
import math
import os
import random
import shutil
import string
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from schdoc import read_stream, split, join, field, set_field, owner, write_stream  # noqa: E402

SHEET = os.path.join(os.path.dirname(HERE), 'Asar_feather.PrjPcb', 'asar_a7_0.SchDoc')
GREY = '8421504'
LABELLED = ['JTAG', 'CTRL (7)', 'ADDRESS (15)', 'DATA (16)', 'DQ[3:0]', 'SD-DAT[3:0]', 'CHAN-I/O (18)']
SEEDS = {'STEMMA QT -> FPGA': (721.0, 760.0), 'LED/Button <-> FPGA': (712.0, 590.0)}


def bgr(rgb):
    return ((rgb & 0xFF) << 16) | (rgb & 0xFF00) | (rgb >> 16)


def num(b, k):
    v, f = field(b, k), field(b, k + '_Frac')
    return (int(v) if v else 0) + (int(f) / 100000.0 if f else 0.0)


def key(p):
    return (round(p[0], 4), round(p[1], 4))


def on(a, p, q, tol=1e-6):
    (x, y), (x1, y1), (x2, y2) = a, p, q
    if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) > tol * max(1.0, math.hypot(x2 - x1, y2 - y1)):
        return False
    return min(x1, x2) - tol <= x <= max(x1, x2) + tol and min(y1, y2) - tol <= y <= max(y1, y2) + tol


def crossings(p, q, r, s):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p, q, r, s
    d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(d) < 1e-12:
        return [a for a in (r, s) if on(a, p, q)] + [a for a in (p, q) if on(a, r, s)]
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
    e = 1e-9
    return [(x1 + t * (x2 - x1), y1 + t * (y2 - y1))] if -e <= t <= 1 + e and -e <= u <= 1 + e else []


def faces(segs):
    """Bounded faces (counter-clockwise vertex lists) of the planar graph the segments form."""
    cuts = defaultdict(list)
    for i, (p, q) in enumerate(segs):
        cuts[i] += [p, q]
        for j in range(i + 1, len(segs)):
            r, s = segs[j]
            if max(p[0], q[0]) < min(r[0], s[0]) - 1e-6 or max(r[0], s[0]) < min(p[0], q[0]) - 1e-6:
                continue
            if max(p[1], q[1]) < min(r[1], s[1]) - 1e-6 or max(r[1], s[1]) < min(p[1], q[1]) - 1e-6:
                continue
            for x in crossings(p, q, r, s):
                cuts[i].append(x)
                cuts[j].append(x)
    edges = set()
    for i, (p, q) in enumerate(segs):
        pts = sorted({key(x) for x in cuts[i]}, key=lambda x: math.hypot(x[0] - p[0], x[1] - p[1]))
        for a, b in zip(pts, pts[1:]):
            edges |= {(a, b), (b, a)}
    nbr = defaultdict(list)
    for a, b in edges:
        nbr[a].append(b)
    for a in nbr:
        nbr[a].sort(key=lambda b: math.atan2(b[1] - a[1], b[0] - a[0]))
    seen, out = set(), []
    for e in edges:
        if e in seen:
            continue
        f, cur = [], e
        while cur not in seen:
            seen.add(cur)
            a, b = cur
            f.append(a)
            nb = nbr[b]
            cur = (b, nb[(nb.index(a) - 1) % len(nb)])
        area = 0.5 * sum(f[i][0] * f[i - 1][1] * -1 + f[i - 1][0] * f[i][1] for i in range(len(f)))
        if area > 0:
            out.append((area, f))
    return out


def inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def simplify(f):
    """Drop collinear intermediate vertices."""
    out = []
    n = len(f)
    for i in range(n):
        a, b, c = f[i - 1], f[i], f[(i + 1) % n]
        if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) > 1e-9:
            out.append(b)
    return out


def coord(k, v):
    i = math.floor(v + 1e-9)
    fr = int(round((v - i) * 100000))
    return '|%s=%d' % (k, i) + ('|%s_Frac=%d' % (k, fr) if fr else '')


def text(b):
    return b.decode('latin-1', 'replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arrow', default='0xFFCC99', help='arrow fill as 0xRRGGBB (default light orange)')
    ap.add_argument('--text', default='0x000000', help='label colour as 0xRRGGBB (default black)')
    ap.add_argument('--src', default=SHEET)
    ap.add_argument('--out', default=None)
    ap.add_argument('--preview', default=None, help='write a PNG of the picked arrows and stop')
    a = ap.parse_args()

    recs = split(read_stream(a.src))
    assert text(recs[0][1]).startswith('|HEADER=') and text(recs[1][1]).startswith('|RECORD=31|')
    if any(text(b).startswith('|RECORD=7|') and field(b, 'IsSolid') == 'T' for _, b in recs):
        sys.exit('Refusing: the sheet already has a filled polygon.')
    segs, labels, boxes = [], {}, []
    for _, b in recs:
        if field(b, 'OwnerIndex') is not None:
            continue
        t = text(b)
        if t.startswith('|RECORD=6|'):
            pts = [(num(b, 'X%d' % i), num(b, 'Y%d' % i)) for i in range(1, int(field(b, 'LocationCount')) + 1)]
            segs += list(zip(pts, pts[1:]))
        elif t.startswith('|RECORD=4|'):
            labels[field(b, 'Text')] = (num(b, 'Location.X') + 2, num(b, 'Location.Y') + 2)
        elif t.startswith('|RECORD=14|'):
            boxes.append((num(b, 'Location.X'), num(b, 'Location.Y'), num(b, 'Corner.X'), num(b, 'Corner.Y')))
    fs = faces(segs)
    seeds = dict(SEEDS)
    for name in LABELLED:
        assert name in labels, 'label %r not on the sheet' % name
        seeds[name] = labels[name]
    picked = {}
    for name, pt in seeds.items():
        hits = sorted((ar, f) for ar, f in fs if inside(pt, f))
        assert hits, 'no face around %s' % name
        ar, f = hits[0]
        g = simplify(f)
        diag = sum(1 for i in range(len(g)) if g[i - 1][0] != g[i][0] and g[i - 1][1] != g[i][1])
        xs, ys = [p[0] for p in g], [p[1] for p in g]
        is_box = any(abs(min(xs) - x0) < 1e-6 and abs(min(ys) - y0) < 1e-6 and abs(max(xs) - x1) < 1e-6 and abs(max(ys) - y1) < 1e-6
                     for x0, y0, x1, y1 in boxes)
        assert diag >= 2 and not is_box and 300 < ar < 5000, '%s picked a face that is not an arrow (area %.0f, %d diagonals)' % (name, ar, diag)
        picked[name] = g
        print('  %-20s area %6.0f  %2d vertices  %d diagonals  bbox (%.1f,%.1f)-(%.1f,%.1f)' % (name, ar, len(g), diag, min(xs), min(ys), max(xs), max(ys)))
    assert len({tuple(g) for g in picked.values()}) == len(picked), 'two seeds picked the same face'
    print('%d arrows' % len(picked))

    if a.preview:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        rgb_a, rgb_t = int(a.arrow, 16), int(a.text, 16)
        fig, ax = plt.subplots(figsize=(12, 10))
        for x0, y0, x1, y1 in boxes:
            ax.fill([x0, x1, x1, x0], [y0, y0, y1, y1], color='#87CEEB')
        for g in picked.values():
            ax.fill([p[0] for p in g], [p[1] for p in g], color='#%06X' % rgb_a)
        for p, q in segs:
            ax.plot([p[0], q[0]], [p[1], q[1]], color='#800000', lw=0.8)
        for t, (x, y) in labels.items():
            ax.text(x - 2, y - 2, t, fontsize=6, color='#%06X' % rgb_t)
        ax.set_xlim(110, 820); ax.set_ylim(400, 1045); ax.set_aspect('equal'); ax.axis('off')
        fig.savefig(a.preview, dpi=110, bbox_inches='tight')
        print('preview', a.preview)
        return

    taken = {field(b, 'UniqueID') for _, b in recs if field(b, 'UniqueID')}
    random.seed(20261108)

    def uid():
        while True:
            u = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
            if u not in taken:
                taken.add(u)
                return u
    fill = bgr(int(a.arrow, 16))
    new = []
    for name in LABELLED + list(SEEDS):
        g = picked[name]
        body = '|RECORD=7|OwnerPartId=-1|LineWidth=1|Color=128|AreaColor=%d|IsSolid=T|LocationCount=%d' % (fill, len(g))
        for i, (x, y) in enumerate(g, 1):
            body += coord('X%d' % i, x) + coord('Y%d' % i, y)
        new.append([b'\x00\x00\x00\x00', (body + '|UniqueID=%s' % uid()).encode('latin-1') + b'\x00'])
    at = 2
    while text(recs[at][1]).startswith('|RECORD=14|'):              # after the block fills
        at += 1
    n = len(new)
    tcol = str(bgr(int(a.text, 16)))
    out, recoloured = recs[:at] + new, 0
    for h, b in recs[at:]:
        o = owner(b)
        if o is not None and o >= at:
            b = set_field(b, 'OwnerIndex', str(int(field(b, 'OwnerIndex')) + n))
        if text(b).startswith('|RECORD=4|') and field(b, 'OwnerIndex') is None and field(b, 'Color') == GREY:
            b = set_field(b, 'Color', tcol)
            recoloured += 1
        out.append([h, b])
    assert all(owner(b) is None or owner(b) < at for _, b in recs[:at])
    old_weight = field(recs[0][1], 'Weight')
    out[0] = [out[0][0], set_field(out[0][1], 'Weight', str(len(out) - 1))]
    data = join(out)

    chk = split(data)
    assert len(chk) == len(recs) + n
    for (_, b0), (_, b1) in zip(recs[at:], chk[at + n:]):
        o0 = field(b0, 'OwnerIndex')
        if o0 is not None and int(o0) + 1 >= at:
            assert int(field(b1, 'OwnerIndex')) == int(o0) + n
            b1 = set_field(b1, 'OwnerIndex', o0)
        if text(b0).startswith('|RECORD=4|') and o0 is None and field(b0, 'Color') == GREY:
            assert field(b1, 'Color') == tcol
            b1 = set_field(b1, 'Color', GREY)
        assert b0 == b1, 'record changed: %r' % b0[:80]
    dst = a.out or a.src
    shutil.copy2(a.src, (a.src + '.pre-color') if not a.out else dst)
    write_stream(dst, data)
    print('inserted %d arrow fills (#%06X), recoloured %d labels to #%06X; Weight %s -> %s'
          % (n, int(a.arrow, 16), recoloured, int(a.text, 16), old_weight, field(out[0][1], 'Weight')))


if __name__ == '__main__':
    main()
