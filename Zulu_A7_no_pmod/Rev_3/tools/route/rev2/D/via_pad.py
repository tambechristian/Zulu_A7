"""via_pad.py <base_moved.json> <plan.json>: vias of the plan (new) and of the resulting board whose land overlaps an
SMD pad on a layer of the via's span. Through vias in SMD pads must be 0; microvias are listed."""
import json, math, sys
B = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def span(v): return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
smd = [p for p in B['pads'] if not p['drill']]
def hit(v):
    out = []
    for p in smd:
        if not set(p['layers']) & set(span(v)): continue
        r = v['size'] / 2
        if p['shape'] == 'circle':
            d = math.hypot(v['x'] - p['x'], v['y'] - p['y']) - p['w'] / 2
        else:
            dx = max(abs(v['x'] - p['x']) - p['w'] / 2, 0); dy = max(abs(v['y'] - p['y']) - p['h'] / 2, 0)
            d = math.hypot(dx, dy)
        if d < r - 1e-6: out.append('%s-%s(%s)' % (p['ref'], p['pad'], p['net']))
    return out
rv = {(v['net'], round(v['x'], 3), round(v['y'], 3)) for v in P.get('remove_vias', [])}
for tag, vs in (('NEW', P['vias']), ('BOARD-KEPT', [v for v in B['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3)) not in rv])):
    th = mv = 0
    for v in vs:
        h = hit(v)
        if not h: continue
        through = span(v) == STACK
        th += through; mv += not through
        if tag == 'NEW' or through:
            print(tag, 'THROUGH' if through else 'uvia', v['net'], v['x'], v['y'], '>'.join(s[:2] for s in span(v)), h)
    print('%s: through-in-SMD-pad %d, microvia-in-SMD-pad %d' % (tag, th, mv))
