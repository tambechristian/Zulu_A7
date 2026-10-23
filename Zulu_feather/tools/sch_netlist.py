"""Netlist straight from the SchDoc files, so file-level schematic edits can be checked by netlist diff.

The project is flat (HierarchyMode=0) with no ports, buses or sheet entries: net labels (RECORD=25) and
power ports (RECORD=17) name nets project-wide, which is how the KiCad conversion read it too.
Connectivity rules (Altium's): a wire endpoint, pin hot spot, label or port joins a wire when it lies
on any of the wire's segments; two wires join where an endpoint of one lies on the other, or at a
junction (RECORD=29). Only the pins of each placed part's CurrentPartId count.

    python tools/sch_netlist.py <project folder> [--compare <kicad netlist>]
"""
import glob
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import field, read_stream, split  # noqa: E402

DIRS = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}


def num(b, k):
    v, f = field(b, k), field(b, k + '_Frac')
    return round((int(v) if v else 0) + (int(f) if f else 0) / 1e5, 4)


def owner(b):
    v = field(b, 'OwnerIndex')
    return int(v) + 1 if v is not None else None


def on_segment(p, a, b, eps=1e-3):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if min(x1, x2) - eps <= x <= max(x1, x2) + eps and min(y1, y2) - eps <= y <= max(y1, y2) + eps:
        return abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) <= eps * max(1, abs(x2 - x1) + abs(y2 - y1))
    return False


def sheet_objects(path, recs=None):
    """Return (pins, wires, junctions, labels) for one sheet (from the file, or from recs if given).

    pins: [(ref, designator, (x, y))], wires: [[(x, y), ...]], labels: [(text, (x, y))]."""
    if recs is None:
        recs = split(read_stream(path))
    comps, refs = {}, {}
    for i, (h, b) in enumerate(recs):
        r = field(b, 'RECORD')
        if r == '1':
            comps[i] = field(b, 'CurrentPartId') or '1'
        elif r == '34' and owner(b) is not None:
            refs[owner(b)] = field(b, 'Text')
    pins, wires, juncs, labels = [], [], [], []
    for i, (h, b) in enumerate(recs):
        r = field(b, 'RECORD')
        if r == '2':
            c = owner(b)
            if c not in comps or field(b, 'OwnerPartId') not in (comps[c], '-1', None):
                continue
            cong = int(field(b, 'PinConglomerate') or 0)
            ln = num(b, 'PinLength')
            dx, dy = DIRS[cong & 3]
            p = (round(num(b, 'Location.X') + dx * ln, 4), round(num(b, 'Location.Y') + dy * ln, 4))
            pins.append((refs.get(c), field(b, 'Designator'), p))
        elif r == '27' and owner(b) in (None, 0):
            n = int(field(b, 'LocationCount'))
            wires.append([(num(b, 'X%d' % k), num(b, 'Y%d' % k)) for k in range(1, n + 1)])
        elif r == '29' and field(b, 'OwnerPartId') in ('-1', None):
            juncs.append((num(b, 'Location.X'), num(b, 'Location.Y')))
        elif r in ('25', '17'):
            labels.append((field(b, 'Text'), (num(b, 'Location.X'), num(b, 'Location.Y'))))
    return pins, wires, juncs, labels


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def build(folder):
    """Return {net name: sorted [(ref, pin)]} for the whole project."""
    d = DSU()
    for path in sorted(glob.glob(os.path.join(folder, '*.SchDoc'))):
        s = os.path.basename(path)
        pins, wires, juncs, labels = sheet_objects(path)
        segs = [(wi, a, b) for wi, w in enumerate(wires) for a, b in zip(w, w[1:])]
        for wi, w in enumerate(wires):
            d.find((s, 'w', wi))
            for p in (w[0], w[-1]):
                for wj, a, b in segs:
                    if wj != wi and on_segment(p, a, b):
                        d.union((s, 'w', wi), (s, 'w', wj))
        for j in juncs:
            hit = [wi for wi, a, b in segs if on_segment(j, a, b)]
            for wi in hit[1:]:
                d.union((s, 'w', hit[0]), (s, 'w', wi))
        pin_at = defaultdict(list)
        for ref, des, p in pins:
            node = ('pin', ref, des)
            d.find(node)
            pin_at[p].append(node)
            for wi, a, b in segs:
                if on_segment(p, a, b):
                    d.union(node, (s, 'w', wi))
        for p, nodes in pin_at.items():           # pin touching pin
            for n in nodes[1:]:
                d.union(nodes[0], n)
        for text, p in labels:
            name = ('net', text)
            d.find(name)
            for wi, a, b in segs:
                if on_segment(p, a, b):
                    d.union(name, (s, 'w', wi))
            for n in pin_at.get(p, []):
                d.union(name, n)
    groups = defaultdict(list)
    for node in list(d.p):
        groups[d.find(node)].append(node)
    nets = {}
    for g in groups.values():
        names = sorted(n[1] for n in g if n[0] == 'net')
        pins = sorted((n[1], n[2]) for n in g if n[0] == 'pin')
        if not pins:
            continue
        if len(set(names)) > 1:
            name = '+'.join(sorted(set(names)))     # a short between two named nets
        elif names:
            name = names[0]
        else:
            name = 'N$' + '-'.join(pins[0])
        nets.setdefault(name, []).extend(pins)
    return {k: sorted(set(v)) for k, v in nets.items()}


def main():
    folder = sys.argv[1]
    nets = build(folder)
    if '--compare' in sys.argv:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sexpr
        ref = sexpr.netlist(sys.argv[sys.argv.index('--compare') + 1])
        a = {frozenset(v) for v in nets.values() if len(v) > 1}
        b = {frozenset(v) for k, v in ref.items() if len(v) > 1}
        print('multi-pin nets: SchDoc %d, reference %d, identical %d' % (len(a), len(b), len(a & b)))
        for s in sorted(a - b, key=len)[:10]:
            print('  only SchDoc:', sorted(s)[:8])
        for s in sorted(b - a, key=len)[:10]:
            print('  only reference:', sorted(s)[:8])
        shorts = [k for k in nets if '+' in k]
        print('named-net merges:', shorts)
        return 0 if a == b and not shorts else 1
    for k in sorted(nets):
        print(k, ' '.join('%s-%s' % p for p in nets[k]))


if __name__ == '__main__':
    sys.exit(main())
