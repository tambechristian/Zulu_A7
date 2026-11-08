# KiCad copy: the block diagram (zulu_a7_0.kicad_sch) in the colours of the Altium copies (2026-11-07, user request):
# blocks filled light sky blue (#CDEBF7; #87CEEB at first), thick bus arrows light orange (#FFCC99), labels black.
# --recolor only changes the colour of the 14 block fills already on the sheet.
# The shapes come from the coloured Altium production sheet (Zulu_Altium_VS_Code/.../zulu_a7_0.SchDoc), where
# Asar_feather/tools/fill_block_diagram.py and color_block_diagram.py placed one filled Rectangle per block and one
# filled Polygon per arrow. This script first proves the KiCad sheet draws the same 272 lines (Altium X, Y in 10 mil ->
# KiCad x = 0.254 X, y = 313.182 - 0.254 Y), then adds a filled rectangle / polyline per shape (KiCad draws shape fills
# on the background layer, under every line and text) and gives each of the 50 labels a black font colour.
# Guards: no filled shape on the sheet yet (a rerun stops), every KiCad line matched, 14 rectangles + 9 polygons read.
#   python tools/apply_block_diagram_colors.py kicad_project
import os
import random
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'Asar_feather', 'tools'))
from schdoc import read_stream, split, field  # noqa: E402

ALTIUM = os.path.join(ROOT, 'Zulu_Altium_VS_Code', 'Imported zulu_a7.PrjPcb', 'zulu_a7_0.SchDoc')
H = 313.182                      # sheet height in mm (paper "User" 236.982 313.182)
BLOCK = (205, 235, 247)          # #CDEBF7 (was #87CEEB = 135 206 235)
ARROW = (255, 204, 153)          # #FFCC99


def num(b, k):
    v, f = field(b, k), field(b, k + '_Frac')
    return (int(v) if v else 0) + (int(f) / 100000.0 if f else 0.0)


def mm(x, y):
    return round(x * 0.254, 4), round(H - y * 0.254, 4)


def fmt(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return s if s != '-0' else '0'


def altium_shapes():
    rects, polys, lines = [], [], set()
    for _, b in split(read_stream(ALTIUM)):
        if field(b, 'OwnerIndex') is not None:
            continue
        t = b.decode('latin-1', 'replace')
        if t.startswith('|RECORD=14|') and field(b, 'IsSolid') == 'T':
            rects.append((mm(num(b, 'Location.X'), num(b, 'Location.Y')), mm(num(b, 'Corner.X'), num(b, 'Corner.Y'))))
        elif t.startswith('|RECORD=7|') and field(b, 'IsSolid') == 'T':
            n = int(field(b, 'LocationCount'))
            polys.append([mm(num(b, 'X%d' % i), num(b, 'Y%d' % i)) for i in range(1, n + 1)])
        elif t.startswith('|RECORD=6|'):
            a = mm(num(b, 'X1'), num(b, 'Y1'))
            c = mm(num(b, 'X2'), num(b, 'Y2'))
            lines.add(tuple(sorted([a, c])))
    return rects, polys, lines


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    proj = args[0] if args else os.path.join(os.path.dirname(HERE), 'kicad_project')
    path = os.path.join(proj, 'zulu_a7_0.kicad_sch')
    text = open(path, encoding='utf-8', newline='').read()
    if '--recolor' in sys.argv:
        recolor(path, text)
        return
    if '(type color)' in text:
        raise SystemExit('REFUSED: the sheet already has a colour-filled shape')
    rects, polys, alines = altium_shapes()
    if (len(rects), len(polys)) != (14, 9):
        raise SystemExit('REFUSED: expected 14 block fills and 9 arrow fills in %s, found %d and %d' % (ALTIUM, len(rects), len(polys)))

    lib_end = text.index('\n\t(lib_symbols')
    depth, j = 0, text.index('(lib_symbols')
    while True:
        if text[j] == '(':
            depth += 1
        elif text[j] == ')':
            depth -= 1
            if depth == 0:
                break
        j += 1
    body_start = j + 1
    klines = set()
    for m in re.finditer(r'\n\t\(polyline\n\t\t\(pts\n\t\t\t\(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)\n', text[body_start:]):
        a = (round(float(m.group(1)), 4), round(float(m.group(2)), 4))
        c = (round(float(m.group(3)), 4), round(float(m.group(4)), 4))
        klines.add(tuple(sorted([a, c])))
    # The converter rounded the fractional Altium coordinates (21 lines differ by 0.0001 mm): match within TOL, and
    # snap every fill vertex onto a KiCad line end so the fills meet KiCad's own lines exactly.
    TOL = 0.001

    def close(a, c):
        return max(abs(a[0][0] - c[0][0]), abs(a[0][1] - c[0][1]), abs(a[1][0] - c[1][0]), abs(a[1][1] - c[1][1])) <= TOL
    unmatched = [k for k in klines if k not in alines and not any(close(k, a) for a in alines)]
    if len(klines) != 272 or len(alines) != 272 or unmatched:
        raise SystemExit('REFUSED: KiCad lines (%d) vs Altium lines (%d): %d KiCad lines have no Altium line within %g mm'
                         % (len(klines), len(alines), len(unmatched), TOL))
    ends = {p for k in klines for p in k}

    def snap(p):
        q = min(ends, key=lambda e: max(abs(e[0] - p[0]), abs(e[1] - p[1])))
        return q if max(abs(q[0] - p[0]), abs(q[1] - p[1])) <= TOL else p
    rects = [(snap(a), snap(c)) for a, c in rects]
    polys = [[snap(p) for p in pts] for pts in polys]

    random.seed(20261107)

    def uid():
        return str(uuid.UUID(int=random.getrandbits(128), version=4))

    def stroke_fill(rgb):
        return ('\t\t(stroke\n\t\t\t(width 0.254)\n\t\t\t(type solid)\n\t\t\t(color 128 0 0 1)\n\t\t)\n'
                '\t\t(fill\n\t\t\t(type color)\n\t\t\t(color %d %d %d 1)\n\t\t)\n' % rgb)
    items = []
    for (x0, y0), (x1, y1) in rects:
        items.append('\t(rectangle\n\t\t(start %s %s)\n\t\t(end %s %s)\n%s\t\t(uuid "%s")\n\t)\n'
                     % (fmt(min(x0, x1)), fmt(min(y0, y1)), fmt(max(x0, x1)), fmt(max(y0, y1)), stroke_fill(BLOCK), uid()))
    for pts in polys:
        ring = pts + [pts[0]]
        xy = ' '.join('(xy %s %s)' % (fmt(x), fmt(y)) for x, y in ring)
        items.append('\t(polyline\n\t\t(pts\n\t\t\t%s\n\t\t)\n%s\t\t(uuid "%s")\n\t)\n' % (xy, stroke_fill(ARROW), uid()))

    # black font colour on every top-level text label (none has a colour yet)
    head, body = text[:body_start], text[body_start:]
    labels = re.findall(r'\n\t\(text "', body)
    pat = re.compile(r'(\n\t\(text "[^"]*"\n(?:\t\t[^\n]*\n)*?\t\t\(effects\n\t\t\t\(font\n\t\t\t\t\(size [-\d.]+ [-\d.]+\)\n)(\t\t\t\))')
    body, n = pat.subn(lambda m: m.group(1) + '\t\t\t\t(color 0 0 0 1)\n' + m.group(2), body)
    if n != len(labels) or n != 50:
        raise SystemExit('REFUSED: coloured %d of %d labels (expected 50)' % (n, len(labels)))

    k = body.index('\n\t(text "')            # put the new shapes just before the first label
    body = body[:k + 1] + ''.join(items) + body[k + 1:]
    out = head + body
    assert out.count('(') == out.count(')')
    open(path, 'w', encoding='utf-8', newline='').write(out)
    print('%s: %d block fills, %d arrow fills, %d labels black' % (path, len(rects), len(polys), n))


def recolor(path, text):
    """Change the fill colour of the 14 block rectangles placed by an earlier run; nothing else."""
    blocks = list(re.finditer(r'(?m)^\t\(rectangle\n(?:\t\t[^\n]*\n)*?\t\)\n', text))
    if len(blocks) != 14:
        raise SystemExit('REFUSED: expected 14 block rectangles, found %d' % len(blocks))
    fill_re = re.compile(r'\(fill\n\t\t\t\(type color\)\n\t\t\t(\(color \d+ \d+ \d+ 1\))')
    new = '(color %d %d %d 1)' % BLOCK
    out, last, n = [], 0, 0
    for m in blocks:
        seg = text[m.start():m.end()]
        fill = fill_re.search(seg)
        if not fill:
            raise SystemExit('REFUSED: a block rectangle has no colour fill')
        seg = seg[:fill.start(1)] + new + seg[fill.end(1):]
        out.append(text[last:m.start()] + seg)
        last, n = m.end(), n + 1
    out = ''.join(out) + text[last:]
    # nothing but the 14 fill colours changed
    assert fill_re.sub('X', out) == fill_re.sub('X', text)
    open(path, 'w', encoding='utf-8', newline='').write(out)
    print('%s: %d block fills recoloured to %s' % (path, n, new))


if __name__ == '__main__':
    main()
