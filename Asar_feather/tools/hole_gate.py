"""Hole gate for routing plans (2026-11-06). route_check judges copper, not drills, and missed five GND vias stacked inside a through via
on a trial. Two holes that drill through the same dielectric must keep the board's Hole To Hole rule, edge to edge. Stacked lasers pass: they
meet on one copper layer and share no dielectric.

    python tools/hole_gate.py <plan.json> <model.json> [--rule 0.24]

Reports every offending pair and exits 1 if there is one. The committed plan and the plan with five stacked vias are the controls: 0 and 5 pairs."""
import json
import math
import sys
from collections import defaultdict

SPAN = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
LONG = {'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3'}


def dielectrics(v):
    a, b = SPAN.index(v['from']), SPAN.index(v['to'])
    return set(range(min(a, b), max(a, b)))


def pairs(plan, model, rule):
    vias = model.get('vias', []) + plan['vias']
    grid = defaultdict(list)
    for i, v in enumerate(vias):
        grid[(int(v['x'] // 1), int(v['y'] // 1))].append(i)
    bad = []
    for i, v in enumerate(vias):
        cx, cy = int(v['x'] // 1), int(v['y'] // 1)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), ()):
                    if j <= i:
                        continue
                    w = vias[j]
                    if not dielectrics(v) & dielectrics(w):
                        continue
                    d = math.hypot(v['x'] - w['x'], v['y'] - w['y'])
                    g = d - (v['hole'] + w['hole']) / 2
                    if g < rule:
                        bad.append((round(g, 4), v, w))
    return bad


def show(b):
    g, v, w = b
    return '%.4f %s %.3f,%.3f %s>%s %.2f | %s %.3f,%.3f %s>%s %.2f' % (
        g, v['net'], v['x'], v['y'], v['from'][:3], v['to'][:3], v['hole'], w['net'], w['x'], w['y'], w['from'][:3], w['to'][:3], w['hole'])


if __name__ == '__main__':
    a = sys.argv[1:]
    rule = 0.24
    if '--rule' in a:
        i = a.index('--rule')
        rule = float(a[i + 1])
        del a[i:i + 2]
    plan, model = json.load(open(a[0])), json.load(open(a[1]))
    bad = pairs(plan, model, rule)
    neg = [b for b in bad if b[0] < 0]
    print('%d pairs under %.3f mm edge to edge in the same dielectric, %d of them overlapping' % (len(bad), rule, len(neg)))
    for b in sorted(bad, key=lambda x: x[0])[:12]:
        print('  ', show(b))
    print('PASS' if not bad else 'FAIL')
    sys.exit(1 if bad else 0)
