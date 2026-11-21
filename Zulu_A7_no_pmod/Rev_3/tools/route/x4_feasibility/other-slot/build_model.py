"""Build a router model: X4 -> S2B-PH-SM4-TB at the EAST edge (Top), six 0805 caps moved, foreign copper under the new
pads cut, stubs of removed pads pruned.   python build_model.py caps.json out_model.json"""
import json, math, sys, copy
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
sys.path.insert(0, T)
import route_conn as RC
from scan import fp, tobox, CU, seg_box_gap
M0 = json.load(open(T + '/route/bodies/base.json'))
CFG = json.load(open(sys.argv[1]))
EDGE, SIDE, CX = CFG.get('edge', 'E'), CFG.get('side', 'Top'), CFG['c']
LAY = 'Top Layer' if SIDE == 'Top' else 'Bottom Layer'
M = copy.deepcopy(M0)
moved = set(CFG['caps']) | {'X4'}
old_pads = [p for p in M['pads'] if p['ref'] in moved]
M['pads'] = [p for p in M['pads'] if p['ref'] not in moved]
# new connector pads
pads, body = fp()
names = {'MP1': ('MP1', ''), 'MP2': ('MP2', '')}
pb = {n: tobox(EDGE, CX, (t0, t1, d0, d1)) for n, t0, t1, d0, d1 in pads}
# true pin 1 = VBATT: for E/Top (rot 270) pin 1 is the north signal pad = scan pad '2'
vb, gn = CFG.get('vbatt_pad', '2'), CFG.get('gnd_pad', '1')
new = []
for n, b in pb.items():
    net = 'VBATT' if n == vb else 'GND' if n == gn else ''
    nm = '1' if n == vb else '2' if n == gn else n
    new.append({'ref': 'X4', 'pad': nm, 'net': net, 'x': (b[0] + b[2]) / 2, 'y': (b[1] + b[3]) / 2, 'shape': 'rect',
                'w': b[2] - b[0], 'h': b[3] - b[1], 'layers': [LAY], 'drill': 0.0, 'plated': False})
# moved caps: 0805 pads 1.3 along x 1.5 across at +-0.85
nets = {(p['ref'], p['pad']): p['net'] for p in old_pads}
for ref, (x, y, rot) in CFG['caps'].items():
    for pad, s in (('1', -1), ('2', 1)):
        if rot == 90:
            px, py, w, h = x, y + s * 0.85, 1.5, 1.3
        else:
            px, py, w, h = x + s * 0.85, y, 1.3, 1.5
        new.append({'ref': ref, 'pad': pad, 'net': nets[(ref, pad)], 'x': px, 'y': py, 'shape': 'rect', 'w': w, 'h': h,
                    'layers': ['Top Layer'], 'drill': 0.0, 'plated': False})
# cut foreign copper under/near the new pads
cut_t, cut_v = [], []
newpads = [p for p in new]
def box(p): return (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
keep = []
for t in M['tracks']:
    hit = any(t['layer'] in p['layers'] and t['net'] != p['net'] and seg_box_gap(t, box(p)) < CU for p in newpads)
    (cut_t if hit else keep).append(t)
M['tracks'] = keep
keep = []
for v in M['vias']:
    hit = False
    for p in newpads:
        if p['layers'][0] in v['span'] and v['net'] != p['net']:
            b = box(p); dx = max(b[0] - v['x'], 0, v['x'] - b[2]); dy = max(b[1] - v['y'], 0, v['y'] - b[3])
            if math.hypot(dx, dy) - v['size'] / 2 < CU: hit = True
    (cut_v if hit else keep).append(v)
M['vias'] = keep
M['pads'] += new
# prune stubs left by removed pads (iterative dangling-end removal, only for nets of removed pads + cut nets' pad-less islands)
PL = {'L2-GND': 'GND', 'L5-VCC3V3': 'VCC3V3'}
def touches_end(net, layer, x, y, skip_i):
    for p in M['pads']:
        if p['net'] == net and (p['layers'] is None or layer in p['layers']):
            if RC.pad_point(p, x, y) <= 1e-3: return True
    for v in M['vias']:
        if v['net'] == net and layer in v['span'] and math.hypot(v['x'] - x, v['y'] - y) <= v['size'] / 2 + 1e-3: return True
    for j, t in enumerate(M['tracks']):
        if j == skip_i or t['net'] != net or t['layer'] != layer: continue
        if RC.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], x, y) <= t['w'] / 2 + 1e-3: return True
    return False
def via_links(v):
    n = 0
    for p in M['pads']:
        if p['net'] == v['net'] and any(L in v['span'] for L in (p['layers'] or v['span'])):
            if RC.pad_point(p, v['x'], v['y']) <= v['size'] / 2: n += 1
    for t in M['tracks']:
        if t['net'] == v['net'] and t['layer'] in v['span']:
            if RC.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= t['w'] / 2 + v['size'] / 2: n += 1
    if any(PL.get(L) == v['net'] for L in v['span']): n += 1
    for u in M['vias']:
        if u is not v and u['net'] == v['net'] and set(u['span']) & set(v['span']) and math.hypot(u['x'] - v['x'], u['y'] - v['y']) < 0.05: n += 1
    return n
prune_nets = set(p['net'] for p in old_pads if p['net'])
pruned_t, pruned_v = [], []
changed = True
while changed:
    changed = False
    for i in range(len(M['tracks']) - 1, -1, -1):
        t = M['tracks'][i]
        if t['net'] not in prune_nets: continue
        if not touches_end(t['net'], t['layer'], t['x1'], t['y1'], i) or not touches_end(t['net'], t['layer'], t['x2'], t['y2'], i):
            pruned_t.append(M['tracks'].pop(i)); changed = True
    for i in range(len(M['vias']) - 1, -1, -1):
        v = M['vias'][i]
        if v['net'] not in prune_nets: continue
        if via_links(v) < 2:
            pruned_v.append(M['vias'].pop(i)); changed = True
json.dump(M, open(sys.argv[2], 'w'))
L = lambda ts: sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts)
from collections import Counter
print('cut tracks %d (%.1f mm) by net %s' % (len(cut_t), L(cut_t), dict(Counter(t['net'] for t in cut_t))))
print('cut vias %d by net %s' % (len(cut_v), dict(Counter(v['net'] for v in cut_v))))
print('pruned tracks %d (%.1f mm) %s; pruned vias %d %s' % (len(pruned_t), L(pruned_t), dict(Counter(t['net'] for t in pruned_t)),
      len(pruned_v), dict(Counter(v['net'] for v in pruned_v))))
oc = RC.open_count(RC.islands(M))
print('open after edit:', {k: v for k, v in oc.items() if v}, 'total', sum(oc.values()))
json.dump({'cut_tracks': cut_t, 'cut_vias': cut_v, 'pruned_tracks': pruned_t, 'pruned_vias': pruned_v}, open(sys.argv[2] + '.rip.json', 'w'))
