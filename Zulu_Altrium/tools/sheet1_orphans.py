# -*- coding: utf-8 -*-
"""Sheet 1 (power supplies): what is connected to nothing?  Read-only report.

    python tools/sheet1_orphans.py [sheet-number]      default 1

Asked 2026-09-16: remove the unconnected wires, the unconnected VCC3V3 source component and the
unconnected GND component at the bottom right of sheet 1.  Before anything is deleted this lists,
from the .SchDoc records themselves:

  * every wire, with each end's attachment (pin / port / label / junction / another wire / NOTHING)
    and whether the whole wire is an island (touches no pin, port or label through any chain of
    wires);
  * every component whose pins all touch nothing -- including supply symbols that EAGLE imported as
    parts rather than power ports -- with its designator, library reference, comment and position;
  * every power port and net label that sits on nothing;
  * the page size, so "bottom right" is a coordinate, not an impression.

Altium schematic Y grows upward; the sheet's origin is its bottom-left corner.
"""
import collections
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fix_text_orientation import read_stream, split, field

PRJ = os.path.join(os.path.dirname(HERE), 'Imported zulu_a7.PrjPcb')
DIR = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}
TOL = 1.2


def num(b, k):
    v = field(b, k)
    if v is None:
        return None
    f = field(b, k + '_Frac')
    return int(v) + (int(f) / 1e5 if f else 0.0)


def oi(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def on_segment(px, py, a, b, tol=TOL):
    (ax, ay), (bx, by) = a, b
    if min(ax, bx) - tol <= px <= max(ax, bx) + tol and min(ay, by) - tol <= py <= max(ay, by) + tol:
        cross = abs((bx - ax) * (py - ay) - (by - ay) * (px - ax))
        return cross / (math.hypot(bx - ax, by - ay) or 1) <= tol
    return False


def main():
    sheet = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    path = os.path.join(PRJ, 'zulu_a7_%d.SchDoc' % sheet)
    recs = split(read_stream(path, 'FileHeader'))
    comps, wires, ports, labels, juncs, pins, desig, params = {}, [], [], [], [], [], {}, collections.defaultdict(dict)
    sheet_rec = None
    for i, (h, b) in enumerate(recs):
        r = field(b, 'RECORD')
        if r == '31':
            sheet_rec = b
        elif r == '1':
            comps[i] = b
        elif r == '27':
            n = int(field(b, 'LocationCount') or 0)
            wires.append((i, [(num(b, 'X%d' % k), num(b, 'Y%d' % k)) for k in range(1, n + 1)]))
        elif r == '17':
            ports.append((i, field(b, 'Text'), num(b, 'Location.X'), num(b, 'Location.Y'), field(b, 'Style')))
        elif r == '25':
            labels.append((i, field(b, 'Text'), num(b, 'Location.X'), num(b, 'Location.Y')))
        elif r == '29':
            juncs.append((i, num(b, 'Location.X'), num(b, 'Location.Y')))
        elif r == '34':
            desig[oi(b)] = field(b, 'Text')
        elif r == '41':
            params[oi(b)][field(b, 'Name')] = field(b, 'Text')
    for i, (h, b) in enumerate(recs):
        if field(b, 'RECORD') == '2' and oi(b) in comps:
            x, y = num(b, 'Location.X'), num(b, 'Location.Y')
            c = int(field(b, 'PinConglomerate') or 32)
            ln = int(field(b, 'PinLength') or 0)
            dx, dy = DIR[c & 3]
            pins.append((i, oi(b), field(b, 'Designator'), field(b, 'Name'), x + dx * ln, y + dy * ln))

    if sheet_rec is not None:
        print('sheet %d: SheetStyle=%s  CustomX=%s CustomY=%s  UseCustomSheet=%s' % (
            sheet, field(sheet_rec, 'SheetStyle'), field(sheet_rec, 'CustomX'), field(sheet_rec, 'CustomY'),
            field(sheet_rec, 'UseCustomSheet')))
    xs = [p for _, pts in wires for p in pts] + [(x, y) for _, _, x, y, _ in ports] + [(p[4], p[5]) for p in pins]
    print('object extent: x %.0f..%.0f, y %.0f..%.0f\n' % (min(a for a, _ in xs), max(a for a, _ in xs), min(b for _, b in xs), max(b for _, b in xs)))

    def at_pin(x, y):
        return [p for p in pins if abs(p[4] - x) <= TOL and abs(p[5] - y) <= TOL]

    def at_port(x, y):
        return [p for p in ports if abs(p[2] - x) <= TOL and abs(p[3] - y) <= TOL]

    def at_label(x, y):
        return [l for l in labels if abs(l[2] - x) <= TOL and abs(l[3] - y) <= TOL]

    def wires_through(x, y, skip):
        return [w for w in wires if w[0] != skip and any(on_segment(x, y, a, b) for a, b in zip(w[1], w[1][1:]))]

    # wire islands: union wires that touch; an island is live if any of its wires reaches a pin/port/label
    parent = {w[0]: w[0] for w in wires}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for w in wires:
        for (x, y) in w[1]:
            for o in wires_through(x, y, w[0]):
                parent[find(w[0])] = find(o[0])
    live = set()
    for w in wires:
        for (x, y) in w[1]:
            if at_pin(x, y) or at_port(x, y) or at_label(x, y):
                live.add(find(w[0]))
        # a pin/port/label may also sit on a wire's interior
        for p in pins:
            if any(on_segment(p[4], p[5], a, b) for a, b in zip(w[1], w[1][1:])):
                live.add(find(w[0]))
        for p in ports + labels:
            if any(on_segment(p[2], p[3], a, b) for a, b in zip(w[1], w[1][1:])):
                live.add(find(w[0]))
    print('WIRES (%d)' % len(wires))
    dead = 0
    for w in wires:
        ends = []
        for (x, y) in (w[1][0], w[1][-1]):
            what = []
            if at_pin(x, y):
                what.append('pin ' + ','.join('%s-%s' % (desig.get(p[1], '?'), p[2]) for p in at_pin(x, y)))
            if at_port(x, y):
                what.append('port ' + ','.join(str(p[1]) for p in at_port(x, y)))
            if at_label(x, y):
                what.append('label ' + ','.join(str(l[1]) for l in at_label(x, y)))
            if any(abs(jx - x) <= TOL and abs(jy - y) <= TOL for _, jx, jy in juncs):
                what.append('junction')
            if wires_through(x, y, w[0]):
                what.append('wire')
            ends.append('+'.join(what) or 'NOTHING')
        island = find(w[0]) not in live
        if island or 'NOTHING' in ends:
            dead += 1
            print('  rec %4d  %-40s ends: %-30s | %-30s %s' % (w[0], ' '.join('(%.0f,%.0f)' % p for p in w[1]), ends[0], ends[1],
                                                         'ISLAND: reaches no pin, port or label' if island else 'dangling end'))
    print('  %d wire(s) listed above; the rest are attached at both ends\n' % dead)

    print('COMPONENTS WITH NO PIN CONNECTED')
    for ci, b in sorted(comps.items()):
        ps = [p for p in pins if p[1] == ci]
        hit = []
        for p in ps:
            x, y = p[4], p[5]
            c = bool(at_port(x, y) or at_label(x, y) or wires_through(x, y, None) or
                     [q for q in pins if q[1] != ci and abs(q[4] - x) <= TOL and abs(q[5] - y) <= TOL])
            hit.append(c)
        if ps and not any(hit):
            print('  rec %4d  %-8s lib %-24s comment %-16s at (%s, %s)  pins %s' % (
                ci, desig.get(ci), field(b, 'LibReference'), params[ci].get('Comment'), num(b, 'Location.X'), num(b, 'Location.Y'),
                ' '.join('%s:%s' % (p[2], p[3]) for p in ps)))
    print('\nPOWER PORTS AND LABELS ON NOTHING')
    for p in ports:
        if not (at_pin(p[2], p[3]) or wires_through(p[2], p[3], None)):
            print('  port  rec %4d  %-10s style %s at (%.0f, %.0f)' % (p[0], p[1], p[4], p[2], p[3]))
    for l in labels:
        if not (at_pin(l[2], l[3]) or wires_through(l[2], l[3], None)):
            print('  label rec %4d  %-10s at (%.0f, %.0f)' % (l[0], l[1], l[2], l[3]))


if __name__ == '__main__':
    main()
