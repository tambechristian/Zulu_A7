# -*- coding: utf-8 -*-
"""Is every pad of a PLANE net tied to its plane once these plans are placed?

    python tools/stage5/tie_check.py [--inputs F] [--net VCC3V3] [--pads C3-1,...] plan.json [...]

Stage 5 turns L5 from a GND plane into a VCC3V3 plane, so VCC3V3 stops being a routed net and
becomes a plane net: a VCC3V3 pad is CONNECTED when it reaches the plane, not when it reaches the
regulator through copper.  This is the same test tools/stage4b/gnd_check.py applies to GND:

  A plane-net SMD pad is TIED when its copper island (block_place.islands -- pads, tracks and vias
  joined END TO END, board plus the plans, with the plans' removals applied to the board first)
  holds a via or a through-hole pad of that net.  A through-hole pad is tied by its own barrel.

SPANS (2026-09-29, HDI): a via ties only if its span includes the net's plane layer
(tools/hdi.json plane_nets: VCC3V3 -> L5-VCC3V3); a VCC3V3 Top..L2 microvia is legal but ties nothing.

Prints every untied pad, and for the tied ones the copper length from the pad to its nearest via.
Exit 1 if any pad (or any pad named by --pads) is untied.  On the stage-4a board VCC3V3 has 128 pads
(4 TH + 124 SMD) and 51 vias, and NO SMD pad sits on a via -- every one of the 124 needs its island
to reach a via, which is what this gate counts.
"""
import io, json, math, os, sys
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import block_place as BP
import merge as M
import hdi


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    net = opt('--net', 'VCC3V3')
    inp = json.load(io.open(opt('--inputs', os.path.join(TOOLS, 'route_inputs.json')), encoding='utf-8'))
    want = [p for p in opt('--pads', '').split(',') if p]
    skip = set()
    for k in ('--inputs', '--pads', '--net'):
        if k in a:
            skip.add(a.index(k)); skip.add(a.index(k) + 1)
    paths = [p for i, p in enumerate(a) if i not in skip and p.endswith('.json')]
    plan = M.merge(paths)[0] if paths else {'vias': [], 'tracks': []}
    if plan.get('remove'):
        import route_emit as RE
        inp, missing = RE.apply_removals(inp, plan)
        if missing:
            print('REMOVALS DO NOT MATCH THE BOARD: %s' % '; '.join(missing))
            return 2

    isl = BP.islands(inp, plan, net)
    th = {p['ref'] + '-' + str(p['pad']) for p in inp['th_pads'] if p.get('net') == net}
    plane_layer = hdi.load(inp).plane_of.get(net)          # a via ties only if its span reaches this plane
    reaches = lambda v: plane_layer is None or plane_layer in hdi.span_of(v)
    tied = set()
    for s in isl:
        names = {str(x) for x in s}
        if any(n.startswith('via@') and (plane_layer is None or plane_layer in BP.label_span(n)) for n in names) or (names & th):
            tied |= names

    smd = [(p['ref'] + '-' + str(p['pad']), L, p)
           for k, L in (('top_pads', 'Top'), ('bottom_pads', 'Bottom'))
           for p in inp[k] if p.get('net') == net]
    untied = [(nm, L, p) for nm, L, p in smd if nm not in tied]
    vias = [(v['x'], v['y']) for v in plan['vias'] if v.get('net') == net and reaches(v)] + \
           [(v['x'], v['y']) for v in inp['vias'] if v['net'] == net and reaches(v)]
    ths = [(p['x'], p['y']) for p in inp['th_pads'] if p.get('net') == net]
    sinks = vias + ths
    print('%s: %d SMD pads, tied %d, untied %d; %d vias (%d board + %d plan), %d TH pads '
          '(board + %d plan file(s): %d vias, %d tracks, %d removals)'
          % (net, len(smd), len(smd) - len(untied), len(untied), len(sinks) - len(ths),
             sum(1 for v in inp['vias'] if v['net'] == net),
             sum(1 for v in plan['vias'] if v.get('net') == net), len(ths), len(paths),
             len(plan['vias']), len(plan['tracks']),
             len((plan.get('remove') or {}).get('vias', [])) + len((plan.get('remove') or {}).get('tracks', []))))

    if sinks:
        far = sorted(((min(math.hypot(p['x'] - vx, p['y'] - vy) for vx, vy in sinks), nm, L, p)
                      for nm, L, p in smd if nm not in {u[0] for u in untied}), reverse=True)
        print('  tied pads farthest (straight line) from any %s via/TH pad:' % net)
        for d, nm, L, p in far[:10]:
            print('     %-9s %-6s (%7.3f,%7.3f)  %6.3f mm' % (nm, L, p['x'], p['y'], d))

    for nm, L, p in untied:
        print('  UNTIED  %-9s %-6s (%7.3f,%7.3f)' % (nm, L, p['x'], p['y']))
    bad = [nm for nm, L, p in untied]
    if want:
        missing = [w for w in want if w in bad]
        print('  --pads: %d of %d named pads untied' % (len(missing), len(want)))
        return 1 if missing else 0
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
