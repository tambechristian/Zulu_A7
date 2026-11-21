"""check_emit.py <base_moved.json> <plan.json>: emit_copper preconditions -- every remove track / via matches exactly one
board object (emit_copper's own tolerances: 0.002 mm, width / hole, layer / span), no two removes hit the same object,
no zero-length or duplicate added tracks, no added copper identical to copper that stays."""
import json, sys, math
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def span(v): return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
B = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
def tm(a, b):
    if a['net'] != b['net'] or a['layer'] != b['layer'] or abs(a['w'] - b['w']) >= 0.002: return False
    f = lambda p, q: abs(p[0] - q[0]) < 0.002 and abs(p[1] - q[1]) < 0.002
    A1, A2, B1, B2 = (a['x1'], a['y1']), (a['x2'], a['y2']), (b['x1'], b['y1']), (b['x2'], b['y2'])
    return (f(A1, B1) and f(A2, B2)) or (f(A1, B2) and f(A2, B1))
def vm(a, b):
    return a['net'] == b['net'] and abs(a['hole'] - b['hole']) < 0.002 and abs(a['x'] - b['x']) < 0.002 and \
        abs(a['y'] - b['y']) < 0.002 and span(a)[0] == span(b)[0] and span(a)[-1] == span(b)[-1]
bad = 0
hit = {}
for r in P['remove']:
    m = [i for i, t in enumerate(B['tracks']) if tm(r, t)]
    if len(m) != 1: bad += 1; print('remove track matches %d: %s' % (len(m), r))
    for i in m: hit[i] = hit.get(i, 0) + 1
print('remove tracks: %d, multiply-hit board tracks: %d' % (len(P['remove']), sum(1 for v in hit.values() if v > 1)))
hv = {}
for r in P['remove_vias']:
    m = [i for i, v in enumerate(B['vias']) if vm(r, v)]
    if len(m) != 1: bad += 1; print('remove via matches %d: %s' % (len(m), r))
    for i in m: hv[i] = hv.get(i, 0) + 1
print('remove vias: %d, multiply-hit board vias: %d' % (len(P['remove_vias']), sum(1 for v in hv.values() if v > 1)))
keep_t = [t for i, t in enumerate(B['tracks']) if i not in hit]
keep_v = [v for i, v in enumerate(B['vias']) if i not in hv]
z = [t for t in P['tracks'] if math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) < 1e-4]
print('zero-length added tracks: %d' % len(z)); bad += len(z)
d = sum(1 for i, t in enumerate(P['tracks']) for u in P['tracks'][i + 1:] if tm(t, u))
dv = sum(1 for i, v in enumerate(P['vias']) for u in P['vias'][i + 1:] if vm(v, u))
print('duplicate added tracks: %d, vias: %d' % (d, dv)); bad += d + dv
s = sum(1 for t in P['tracks'] if any(tm(t, u) for u in keep_t if u['net'] == t['net']))
sv = sum(1 for v in P['vias'] if any(vm(v, u) for u in keep_v if u['net'] == v['net']))
print('added copies of kept board copper: tracks %d, vias %d' % (s, sv)); bad += s + sv
print('EMIT CHECK', 'PASS' if not bad else 'FAIL (%d)' % bad)
