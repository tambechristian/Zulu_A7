# -*- coding: utf-8 -*-
"""Read the old EAGLE board as a placement source, in PAD SPACE.

The old board Claude_Fable/zulu_a7.c0.brd is on the SAME outline as the new one -- 69.85 x 25.40,
four wires on layer 20, checked here rather than assumed -- and carries a complete, routed
placement. 154 of the 175 components now on the PcbDoc have a position in it.

It cannot be copied across as element x/y, because Altium re-origins a footprint on import: the
number Altium stores as Component.X is not the number EAGLE stored. What IS transferable is where
the copper landed. So every element is reduced to the centre of its PAD BOUNDING BOX in board
coordinates, plus the world offset of its first pad, which together pin down both position and
orientation without either tool's origin being involved.

EAGLE transform, verified against the board bounds in main():
    rx = lx*cos a - ly*sin a ;  ry = lx*sin a + ly*cos a ;  if mirrored: rx = -rx
    world = (ex + rx, ey + ry)
"""
import io
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'Claude_Fable', 'zulu_a7.c0.brd')


def packages(s):
    out = {}
    for chunk in re.split(r'<package name="', s)[1:]:
        name = chunk.split('"')[0]
        body = chunk.split('</package>')[0]
        pads = []
        for m in re.finditer(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)" dy="([\d.]+)"'
                             r'(?:[^/>]*?rot="R(\d+)")?', body):
            dx, dy = float(m.group(4)), float(m.group(5))
            if m.group(6) and int(m.group(6)) % 180 == 90:
                dx, dy = dy, dx
            pads.append((m.group(1), float(m.group(2)), float(m.group(3)), dx, dy))
        for m in re.finditer(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"(?:[^/>]*?drill="([\d.]+)")?'
                             r'(?:[^/>]*?diameter="([\d.]+)")?', body):
            dia = float(m.group(5)) if m.group(5) else (float(m.group(4) or 0.6) * 2)
            pads.append((m.group(1), float(m.group(2)), float(m.group(3)), dia, dia))
        out[name] = pads
    return out


def elements(s):
    out = {}
    for chunk in re.split(r'<element name="', s)[1:]:
        name = chunk.split('"')[0]
        m = re.match(r'[^>]*?package="([^"]*)" value="[^"]*" x="([-\d.]+)" y="([-\d.]+)"([^/>]*)', chunk)
        if not m:
            continue
        r = re.search(r'rot="(M?)R(\d+)"', m.group(4))
        out[name] = dict(pkg=m.group(1), x=float(m.group(2)), y=float(m.group(3)),
                         mirror=bool(r and r.group(1)), rot=int(r.group(2)) if r else 0)
    return out


def world_pads(el, pads):
    """Every pad of one placed element in board mm: (name, x, y, dx, dy)."""
    a = math.radians(el['rot'])
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for nm, lx, ly, dx, dy in pads:
        rx = lx * ca - ly * sa
        ry = lx * sa + ly * ca
        if el['mirror']:
            rx = -rx
        if el['rot'] % 180 == 90:
            dx, dy = dy, dx
        out.append((nm, el['x'] + rx, el['y'] + ry, dx, dy))
    return out


def load(path=OLD):
    """{designator: dict(pkg, side, rot, cx, cy, w, h, p1)} from the old board."""
    s = io.open(path, encoding='utf-8', errors='replace').read()
    pk, el = packages(s), elements(s)
    out = {}
    for d, e in el.items():
        wp = world_pads(e, pk.get(e['pkg'], []))
        if not wp:
            out[d] = dict(pkg=e['pkg'], side='bottom' if e['mirror'] else 'top', rot=e['rot'],
                          cx=e['x'], cy=e['y'], w=0.0, h=0.0, p1=None, npads=0)
            continue
        x0 = min(p[1] - p[3] / 2 for p in wp); x1 = max(p[1] + p[3] / 2 for p in wp)
        y0 = min(p[2] - p[4] / 2 for p in wp); y1 = max(p[2] + p[4] / 2 for p in wp)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        first = min(wp, key=lambda p: (len(p[0]), p[0]))
        out[d] = dict(pkg=e['pkg'], side='bottom' if e['mirror'] else 'top', rot=e['rot'],
                      cx=cx, cy=cy, w=x1 - x0, h=y1 - y0,
                      p1=(first[0], first[1] - cx, first[2] - cy), npads=len(wp))
    return out


def main():
    s = io.open(OLD, encoding='utf-8', errors='replace').read()
    w = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="[^"]*" layer="20"', s)
    xs = [float(v) for seg in w for v in (seg[0], seg[2])]
    ys = [float(v) for seg in w for v in (seg[1], seg[3])]
    print('old outline  %.2f x %.2f mm from %d layer-20 wires' % (max(xs) - min(xs), max(ys) - min(ys), len(w)))
    p = load()
    off = [d for d, v in p.items() if v['npads'] and
           (v['cx'] - v['w'] / 2 < -0.1 or v['cx'] + v['w'] / 2 > max(xs) + 0.1 or
            v['cy'] - v['h'] / 2 < -0.1 or v['cy'] + v['h'] / 2 > max(ys) + 0.1)]
    print('%d elements, %d with pads, %d outside the outline: %s'
          % (len(p), sum(1 for v in p.values() if v['npads']), len(off), sorted(off)))
    for d in sorted(p):
        v = p[d]
        print('  %-6s %-20s %-6s r%-3d  centre %7.3f %7.3f   %5.2f x %5.2f'
              % (d, v['pkg'], v['side'], v['rot'], v['cx'], v['cy'], v['w'], v['h']))


if __name__ == '__main__':
    main()
