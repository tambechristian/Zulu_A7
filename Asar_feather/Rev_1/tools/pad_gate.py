"""Pad-to-pad gate for parts moved after routing (2026-11-06): route_check judges new tracks and vias only, so a pad moved next
to another pad passes it. Checks every different-net SMD pad pair on one side where at least one pad belongs to the given
parts: copper gap against the clearance rule, and the solder-mask web against the board's Minimum Solder Mask Sliver rule.
A web between 0 and the sliver limit is what Altium flags; openings that merge (web <= 0) give no dam at all and are listed too.
Expansion is 0.05 mm per side, 0 on U1 (SolderMaskExpansion_U1). Round U1 lands count as squares here, which is conservative.

    python tools/pad_gate.py <model.json> REF [REF ...]"""
import json
import math
import sys

CLEAR, SLIVER, EXP = 0.0762, 0.1, 0.05


def rect(p):
    return (p['x'] - p['w'] / 2, p['x'] + p['w'] / 2, p['y'] - p['h'] / 2, p['y'] + p['h'] / 2)


def gap(a, b):
    return math.hypot(max(a[0] - b[1], b[0] - a[1], 0), max(a[2] - b[3], b[2] - a[3], 0))


def main():
    M = json.load(open(sys.argv[1]))
    refs = set(sys.argv[2:])
    pads = [p for p in M['pads'] if p['w'] and p['h']]
    bad, rows = [], []
    for p in pads:
        if p['ref'] not in refs:
            continue
        for q in pads:
            if q is p or (q['ref'] in refs and (q['ref'], q['pad']) <= (p['ref'], p['pad'])) or p['net'] == q['net']:
                continue
            if not set(p['layers'] or ['Top Layer', 'Bottom Layer']) & set(q['layers'] or ['Top Layer', 'Bottom Layer']):
                continue
            g = gap(rect(p), rect(q))
            if g > 1.0:
                continue
            web = g - (0 if p['ref'] == 'U1' else EXP) - (0 if q['ref'] == 'U1' else EXP)
            rows.append((g, web, '%s-%s [%s]' % (p['ref'], p['pad'], p['net']), '%s-%s [%s]' % (q['ref'], q['pad'], q['net'])))
            if g < CLEAR or web < SLIVER:
                bad.append(rows[-1])
    rows.sort()
    for r in rows[:8]:
        print('  gap %.4f web %.4f  %s  %s' % r)
    print('%d pairs within 1 mm, %d under clearance %.4f or web %.2f' % (len(rows), len(bad), CLEAR, SLIVER))
    print('PASS' if not bad else 'FAIL')


if __name__ == '__main__':
    main()
