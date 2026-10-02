# -*- coding: utf-8 -*-
"""Which GND SMD pads are tied to the planes once these plans are placed?

    python tools/stage4/gnd_check.py [--inputs F] [--pads C3-1,C4-1,...] plan.json [...]

A GND SMD pad is TIED when its copper island (block_place.islands: pads, tracks and vias joined end to end,
board plus the plans) holds a via or a through-hole GND pad -- both reach the L2/L5 planes (the via by the
Direct plane-connect rule, the TH pad by its own barrel).  Prints every untied pad (or, with --pads, the
named ones) with the length of the tie the plan gives each tied pad; exit 1 if any named / any pad at all
is untied.  Stage 4a (2026-09-21): 103 pads to tie."""
import io, json, math, os, sys
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS); sys.path.insert(0, os.path.join(TOOLS, 'stage3'))
import block_place as BP
import merge as M


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    inp = json.load(io.open(opt('--inputs', os.path.join(TOOLS, 'route_inputs.json')), encoding='utf-8'))
    want = [p for p in opt('--pads', '').split(',') if p]
    skip = set()
    for k in ('--inputs', '--pads'):
        if k in a:
            skip.add(a.index(k)); skip.add(a.index(k) + 1)
    paths = [p for i, p in enumerate(a) if i not in skip and p.endswith('.json')]
    plan = M.merge(paths)[0] if paths else {'vias': [], 'tracks': []}
    isl = BP.islands(inp, plan, 'GND')
    th = {p['ref'] + '-' + str(p['pad']) for p in inp['th_pads'] if p.get('net') == 'GND'}
    tied = set()
    for s in isl:
        names = {str(x) for x in s}
        if any(n.startswith('via@') for n in names) or (names & th):
            tied |= names
    smd = [(p['ref'] + '-' + str(p['pad']), L, p) for k, L in (('top_pads', 'Top'), ('bottom_pads', 'Bottom')) for p in inp[k] if p.get('net') == 'GND']
    untied = [(nm, L, p) for nm, L, p in smd if nm not in tied]
    print('GND SMD pads %d, tied %d, untied %d (board + %d plan file(s): %d vias, %d tracks)' % (
        len(smd), len(smd) - len(untied), len(untied), len(paths), len(plan['vias']), len(plan['tracks'])))
    # tie length: the plan track(s) that end inside the pad, to the nearest plan/board via or TH pad along them
    vias = [(v['x'], v['y']) for v in plan['vias']] + [(v['x'], v['y']) for v in inp['vias'] if v['net'] == 'GND']
    ths = [(p['x'], p['y']) for p in inp['th_pads'] if p.get('net') == 'GND']
    long = []
    for nm, L, p in smd:
        if nm in tied and nm not in {u[0] for u in untied}:
            ends = [t for t in plan['tracks'] if t['net'] == 'GND' and t['layer'] == L and (
                (abs(t['x1'] - p['x']) <= p['sx'] / 2 + 1e-6 and abs(t['y1'] - p['y']) <= p['sy'] / 2 + 1e-6) or
                (abs(t['x2'] - p['x']) <= p['sx'] / 2 + 1e-6 and abs(t['y2'] - p['y']) <= p['sy'] / 2 + 1e-6))]
            for t in ends:
                far = (t['x2'], t['y2']) if abs(t['x1'] - p['x']) <= p['sx'] / 2 + 1e-6 and abs(t['y1'] - p['y']) <= p['sy'] / 2 + 1e-6 else (t['x1'], t['y1'])
                dmin = min([math.hypot(far[0] - vx, far[1] - vy) for vx, vy in vias + ths] or [9])
                Lt = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
                if Lt > 1.5 or dmin > 0.002:
                    long.append((nm, round(Lt, 3), round(dmin, 3)))
    bad = []
    for nm, L, p in untied:
        if not want or nm in want:
            print('  UNTIED %-8s %-6s (%.3f, %.3f)' % (nm, L, p['x'], p['y']))
            bad.append(nm)
    if want:
        missing = [w for w in want if w not in {s[0] for s in smd}]
        if missing:
            print('  not GND SMD pads: %s' % ', '.join(missing))
        print('%d/%d named pads tied' % (len(want) - len(bad), len(want)))
    if long:
        print('ties longer than 1.5 mm or not ending on a via / TH pad: %s' % ', '.join('%s %.2f mm (end %.3f from a via)' % t for t in long[:20]))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
