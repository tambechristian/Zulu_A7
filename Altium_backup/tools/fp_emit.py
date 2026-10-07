# -*- coding: utf-8 -*-
"""Turn a verified land pattern into an EAGLE <package> element.

Footprints reach Altium the same way the rest of the library did: as EAGLE XML inside a throwaway
.brd that the Import Wizard converts (see make_fp_source.py). Writing EAGLE is the cheap half of
that trade -- it is text, it can be diffed, and every number can be asserted before Altium sees it,
whereas a PcbLib is an OLE binary that can only be checked after the fact.

Input is tools/new_footprints.json: a list of
    {"name", "description", "body": {"dx", "dy"}, "pads": [{"name","x","y","dx","dy","shape","drill"}]}
with every dimension in millimetres and the origin at the body centre. drill = 0 means an SMD pad.

Silkscreen is drawn as a body rectangle broken wherever a pad would touch it, plus a pin-1 dot, so
the outline never sits on copper.
"""
import io
import json
import os

SILK_W = 0.127          # 5 mil, the usual EAGLE silk width
SILK_GAP = 0.15         # keep silk this far off any pad
LAYER_SILK = 21         # tPlace
LAYER_DOC = 51          # tDocu
LAYER_NAME = 25         # tNames


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def fmt(v):
    """EAGLE writes plain decimals; keep them short and never in exponent form."""
    s = '%.4f' % round(float(v), 4)
    s = s.rstrip('0').rstrip('.')
    return s if s not in ('', '-0') else '0'


def pad_xml(p):
    if float(p.get('drill', 0)) > 0:
        dia = p.get('diameter') or round(float(p['drill']) + 0.5, 3)
        shape = 'square' if p.get('shape') == 'rect' else 'round'
        return ('<pad name="%s" x="%s" y="%s" drill="%s" diameter="%s" shape="%s"/>'
                % (esc(p['name']), fmt(p['x']), fmt(p['y']), fmt(p['drill']), fmt(dia), shape))
    roundness = ' roundness="100"' if p.get('shape') == 'round' else ''
    return ('<smd name="%s" x="%s" y="%s" dx="%s" dy="%s" layer="1"%s/>'
            % (esc(p['name']), fmt(p['x']), fmt(p['y']), fmt(p['dx']), fmt(p['dy']), roundness))


def _spans(lo, hi, blocks):
    """[lo, hi] minus every [a, b] in blocks, as a list of surviving segments."""
    segs = [(lo, hi)]
    for a, b in blocks:
        nxt = []
        for s, e in segs:
            if b <= s or a >= e:
                nxt.append((s, e))
                continue
            if a > s:
                nxt.append((s, a))
            if b < e:
                nxt.append((b, e))
        segs = nxt
    return [(s, e) for s, e in segs if e - s > 0.2]


def silk_xml(fp):
    """Body rectangle on tPlace, cut wherever a pad is in the way."""
    hx, hy = fp['body']['dx'] / 2.0, fp['body']['dy'] / 2.0
    boxes = []
    for p in fp['pads']:
        if float(p.get('drill', 0)) > 0:
            r = (float(p.get('diameter') or (float(p['drill']) + 0.5))) / 2.0
            boxes.append((p['x'] - r, p['y'] - r, p['x'] + r, p['y'] + r))
        else:
            boxes.append((p['x'] - p['dx'] / 2.0, p['y'] - p['dy'] / 2.0,
                          p['x'] + p['dx'] / 2.0, p['y'] + p['dy'] / 2.0))
    g = SILK_GAP + SILK_W / 2.0
    out = []
    for y in (hy, -hy):
        blocks = [(x0 - g, x1 + g) for x0, y0, x1, y1 in boxes if y0 - g <= y <= y1 + g]
        for a, b in _spans(-hx, hx, blocks):
            out.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>'
                       % (fmt(a), fmt(y), fmt(b), fmt(y), fmt(SILK_W), LAYER_SILK))
    for x in (hx, -hx):
        blocks = [(y0 - g, y1 + g) for x0, y0, x1, y1 in boxes if x0 - g <= x <= x1 + g]
        for a, b in _spans(-hy, hy, blocks):
            out.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>'
                       % (fmt(x), fmt(a), fmt(x), fmt(b), fmt(SILK_W), LAYER_SILK))
    # the body outline again on tDocu, unbroken, so the real extent stays visible
    for x1, y1, x2, y2 in ((-hx, hy, hx, hy), (hx, hy, hx, -hy),
                           (hx, -hy, -hx, -hy), (-hx, -hy, -hx, hy)):
        out.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>'
                   % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), fmt(SILK_W), LAYER_DOC))
    return out


def pin1_dot(fp):
    """A dot outside both the body and pad 1 itself, so no silk lands on copper."""
    one = next((p for p in fp['pads'] if p['name'] == '1'), None)
    if one is None:
        return []
    hx, hy = fp['body']['dx'] / 2.0, fp['body']['dy'] / 2.0
    r, w = 0.1, 0.2
    clear = r + w / 2.0 + SILK_GAP
    if abs(one['x']) > abs(one['y']):                 # pad 1 is on a left/right row
        sgn = 1 if one['x'] > 0 else -1
        x = sgn * (max(hx, abs(one['x']) + one['dx'] / 2.0) + clear)
        y = one['y']
    else:                                             # pad 1 is on a top/bottom row
        sgn = 1 if one['y'] > 0 else -1
        x = one['x']
        y = sgn * (max(hy, abs(one['y']) + one['dy'] / 2.0) + clear)
    return ['<circle x="%s" y="%s" radius="%s" width="%s" layer="%d"/>'
            % (fmt(x), fmt(y), fmt(r), fmt(w), LAYER_SILK)]


def package_xml(fp):
    hy = fp['body']['dy'] / 2.0
    parts = ['<package name="%s">' % esc(fp['name'])]
    if fp.get('description'):
        parts.append('<description>%s</description>' % esc(fp['description']))
    parts += silk_xml(fp)
    parts += pin1_dot(fp)
    parts += [pad_xml(p) for p in fp['pads']]
    parts.append('<text x="%s" y="%s" size="0.8" layer="%d">&gt;NAME</text>'
                 % (fmt(-fp['body']['dx'] / 2.0), fmt(hy + 0.6), LAYER_NAME))
    parts.append('</package>')
    return '\n'.join(parts)


def load(path=None):
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'new_footprints.json')
    with io.open(path, encoding='utf-8') as fh:
        fps = json.load(fh)
    for fp in fps:
        names = [p['name'] for p in fp['pads']]
        assert len(names) == len(set(names)), '%s: duplicate pad names %s' % (fp['name'], names)
        assert fp['body']['dx'] > 0 and fp['body']['dy'] > 0, '%s: no body' % fp['name']
    return fps


if __name__ == '__main__':
    for fp in load():
        print(package_xml(fp))
        print()
