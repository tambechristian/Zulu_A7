"""Survey of the copper around the new X1 and the moved Q1 (model0 = board after placement, before copper edits)."""
import json, math, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
import route_conn as C
M = json.load(open('C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools/route/x1microb/model0.json'))
def pr(o): return {k: o[k] for k in o if k not in ('layers',)}
for ref in ('X1', 'Q1'):
    for p in M['pads']:
        if p['ref'] == ref: print('PAD', pr(p), p['layers'])
def near_t(t, box):
    x0, y0, x1, y1 = box
    return (min(t['x1'], t['x2']) <= x1 and max(t['x1'], t['x2']) >= x0 and min(t['y1'], t['y2']) <= y1 and max(t['y1'], t['y2']) >= y0)
for name, box in (('X1 area', (-0.5, 6.0, 10.5, 16.5)), ('Q1 area', (12.5, 13.0, 19.0, 18.0))):
    print('=====', name)
    for i, t in enumerate(M['tracks']):
        if near_t(t, box): print('T%d' % i, t['net'], t['layer'], t['w'], (t['x1'], t['y1']), (t['x2'], t['y2']))
    for i, v in enumerate(M['vias']):
        if box[0] <= v['x'] <= box[2] and box[1] <= v['y'] <= box[3]: print('V%d' % i, v['net'], (v['x'], v['y']), v['size'], v['hole'], v['span'][0], v['span'][-1])
    for p in M['pads']:
        if p['ref'] not in ('X1', 'Q1') and box[0] <= p['x'] <= box[2] and box[1] <= p['y'] <= box[3]:
            print('P', p['ref'], p['pad'], p['net'], (p['x'], p['y']), p['w'], p['h'], p['layers'][0] if p['layers'] else '-', p.get('drill'))
# clearance: X1/Q1 pads vs other-net copper
CL = 0.09
def pad_rect(p):
    return (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
def rect_seg(r, t):
    # distance from rect to segment (approx via sampling)
    best = 9
    n = 40
    for k in range(n + 1):
        x = t['x1'] + (t['x2'] - t['x1']) * k / n; y = t['y1'] + (t['y2'] - t['y1']) * k / n
        dx = max(r[0] - x, 0, x - r[2]); dy = max(r[1] - y, 0, y - r[3])
        best = min(best, math.hypot(dx, dy))
    return best
print('===== clearance violations of X1/Q1 pads (< %.2f)' % CL)
for p in M['pads']:
    if p['ref'] not in ('X1', 'Q1'): continue
    r = pad_rect(p)
    for i, t in enumerate(M['tracks']):
        if t['net'] == p['net'] or t['layer'] not in p['layers']: continue
        d = rect_seg(r, t) - t['w'] / 2
        if d < CL: print(' ', p['ref'], p['pad'], p['net'], 'vs T%d' % i, t['net'], t['layer'], round(d, 3))
    for i, v in enumerate(M['vias']):
        if v['net'] == p['net'] or not set(v['span']) & set(p['layers']): continue
        dx = max(r[0] - v['x'], 0, v['x'] - r[2]); dy = max(r[1] - v['y'], 0, v['y'] - r[3])
        d = math.hypot(dx, dy) - v['size'] / 2
        if d < CL: print(' ', p['ref'], p['pad'], p['net'], 'vs V%d' % i, v['net'], round(d, 3))
isl = C.islands(M)
print('===== islands of the open nets')
for net in ('GND', 'USB5V0', 'USB_D_N', 'USB_D_P', 'VCC3V3', 'CLK-12M-SHARED', 'VU'):
    I = isl.get(net, [])
    multi = [i for i in I if i['pads']]
    if net in ('GND', 'VCC3V3'):
        multi = [i for i in multi if not i['plane']]
    print(net, len(I), 'islands; with pads (off-plane for plane nets):', len(multi))
    for i in multi[:12]:
        print('   pads', [(M['pads'][k]['ref'], M['pads'][k]['pad']) for k in i['pads']][:8], 'tracks', len(i['tracks']), 'vias', len(i['vias']), 'plane', i['plane'])
