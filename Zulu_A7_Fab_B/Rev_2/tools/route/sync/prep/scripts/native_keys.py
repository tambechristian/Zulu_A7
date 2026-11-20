"""Cross-check a plan's removals against TARGET's NATIVE Altium coordinates (the inventory's olefile extract of the
same 33023787 PcbDoc), with SOURCE's emit_delta.py exact keys (0.1 um integers, net|layer|width|ends ordered;
vias net|x|y|hole|size|upper|lower). emit_delta refuses unless every key selects exactly one board object, so a key
that only matches the KiCad-imported model (route_model.py) within the 0.002 mm emit_copper tolerance is reported.

    python scripts/native_keys.py <plan.json> [native tgt.json]
"""
import json
import os
import sys
from collections import Counter

NATIVE = 'C:/Users/tambe/AppData/Local/Temp/claude/4f46ee6af972add9/cb02897e-21a5-48d4-9f87-57145adc4da2/scratchpad/sync/board/json/tgt.json'
CODE = {'Top Layer': 'T', 'L2-GND': '2', 'L3-SIG': '3', 'L4-SIG': '4', 'L5-VCC3V3': '5', 'Bottom Layer': 'B',
        'Top': 'T', 'Bottom': 'B'}
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def u(x):
    return int(round(x * 10000))


def tkey(t):
    a, b, c, d = u(t['x1']), u(t['y1']), u(t['x2']), u(t['y2'])
    if a > c or (a == c and b > d):
        a, b, c, d = c, d, a, b
    return '%s|%s|%d|%d|%d|%d|%d' % (t['net'], CODE[t['layer']], u(t['w']), a, b, c, d)


def vkey(v):
    sp = v['span'] if 'span' in v else [v['from'], v['to']]
    return '%s|%d|%d|%d|%d|%s|%s' % (v['net'], u(v['x']), u(v['y']), u(v['hole']), u(v['size']), CODE[sp[0]], CODE[sp[-1]])


def main():
    P = json.load(open(sys.argv[1]))
    N = json.load(open(sys.argv[2] if len(sys.argv) > 2 else NATIVE))
    nt = Counter(tkey(t) for t in N['tracks'] if t['layer'] in CODE and t['net'] and t['polygon'] == 65535
                 and t['comp'] is None and not t['keepout'])
    nv = Counter(vkey(v) for v in N['vias'] if v['net'])
    bad_t = [tkey(t) for t in P['remove'] if nt[tkey(t)] != 1]
    bad_v = [vkey(v) for v in P['remove_vias'] if nv[vkey(v)] != 1]
    dup = len(P['remove']) - len({tkey(t) for t in P['remove']}) + len(P['remove_vias']) - len({vkey(v) for v in P['remove_vias']})
    print('%s: %d track + %d via removals; native-key misses: %d tracks, %d vias; duplicate keys in plan: %d' % (
        os.path.basename(sys.argv[1]), len(P['remove']), len(P['remove_vias']), len(bad_t), len(bad_v), dup))
    for k in (bad_t + bad_v)[:20]:
        print('   ', k)
    return 0 if not bad_t and not bad_v and not dup else 1


if __name__ == '__main__':
    sys.exit(main())
