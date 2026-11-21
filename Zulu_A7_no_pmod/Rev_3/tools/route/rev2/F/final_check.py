"""final_check.py <base_moved.json> <model_base.json> <plan.json>
Strategy F gate extras on a composed plan applied to base_moved (compose_plan.apply):
  1. KEPT copper vs MOVED lands: route_check only checks the plan's new items, so every track / via of the final
     board is checked exactly against every moved pad (clearance per layer, hole-to-hole 0.24 to drilled pads);
  2. vias in SMD pads: every via land on Top / Bottom that overlaps an SMD pad of that layer (through vias are a
     violation; microvias are listed with their pad and whether the net matches), new (plan) vs old;
  3. dead copper (prune_stubs.analyse) and open connections (route_conn);
  4. USB_D_P / USB_D_N: length of each net's copper, the length run coupled (centre distance 0.30 +- 0.01 on the
     same layer), and vias on the pair."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import compose_plan as CP  # noqa: E402
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

STACK = R.STACK


def pad_layers(p):
    return p['layers'] or (STACK if p['drill'] else [])


def clr(a, b, l):
    return max(R.clearance(a, l), R.clearance(b or '', l))


def usb(M):
    out = {}
    tr = {n: [t for t in M['tracks'] if t['net'] == n] for n in ('USB_D_P', 'USB_D_N')}
    for n, ts in tr.items():
        out[n] = round(sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts), 4)
    other = tr['USB_D_N']
    cl = 0.0
    for t in tr['USB_D_P']:
        L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
        n = max(1, int(L / 0.005))
        for k in range(n):
            s = (k + 0.5) / n
            x, y = t['x1'] + (t['x2'] - t['x1']) * s, t['y1'] + (t['y2'] - t['y1']) * s
            d = min(C.seg_dist(o['x1'], o['y1'], o['x2'], o['y2'], x, y) for o in other if o['layer'] == t['layer'])
            if abs(d - 0.30) <= 0.01:
                cl += L / n
    out['coupled_P'] = round(cl, 3)
    out['mismatch'] = round(out['USB_D_N'] - out['USB_D_P'], 4)
    out['vias'] = sum(1 for v in M['vias'] if v['net'] in ('USB_D_P', 'USB_D_N'))
    out['layers'] = sorted({t['layer'] for ts in tr.values() for t in ts})
    out['widths'] = sorted({t['w'] for ts in tr.values() for t in ts})
    return out


def main():
    B = json.load(open(sys.argv[1]))
    O = json.load(open(sys.argv[2]))
    P = json.load(open(sys.argv[3]))
    M = CP.apply(B, P)
    moved = [n for o, n in zip(O['pads'], B['pads']) if (o['x'], o['y']) != (n['x'], n['y'])]
    bad = []
    for t in M['tracks']:
        for p in moved:
            if t['layer'] not in pad_layers(p) or (p['net'] and p['net'] == t['net']):
                continue
            g = C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2
            if g < clr(t['net'], p['net'], t['layer']) - 1e-4:
                bad.append('track %s %s (%.3f,%.3f)-(%.3f,%.3f) %.4f from %s.%s' % (
                    t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'], g, p['ref'], p['pad']))
    for v in M['vias']:
        for p in moved:
            pl = pad_layers(p)
            for l in v['span']:
                if l in pl and not (p['net'] and p['net'] == v['net']):
                    g = C.pad_point(p, v['x'], v['y']) - v['size'] / 2
                    if g < clr(v['net'], p['net'], l) - 1e-4:
                        bad.append('via %s (%.3f,%.3f) %s %.4f from %s.%s' % (v['net'], v['x'], v['y'], l, g, p['ref'], p['pad']))
            if p['drill'] and set(v['span']) & set(pl):
                d = math.hypot(v['x'] - p['x'], v['y'] - p['y']) - v['hole'] / 2 - p['drill'] / 2
                if d < R.HOLE_HOLE - 1e-4:
                    bad.append('hole via %s (%.3f,%.3f) %.4f from %s.%s' % (v['net'], v['x'], v['y'], d, p['ref'], p['pad']))
    bad = sorted(set(bad))
    print('kept/new copper vs moved lands: %d violations' % len(bad))
    for b in bad[:20]:
        print('  ' + b)
    newv = {CP.vkey(dict(v, span=CP.vspan(v))) for v in P['vias']}
    thr, micro = [], []
    for v in M['vias']:
        for p in M['pads']:
            if p['drill']:
                continue
            for l in ('Top Layer', 'Bottom Layer'):
                if l in v['span'] and l in (p['layers'] or []) and C.pad_point(p, v['x'], v['y']) < v['size'] / 2 - 1e-6:
                    rec = '%s (%.3f,%.3f) %.2f/%.2f %s>%s in %s.%s [%s] on %s%s%s' % (
                        v['net'], v['x'], v['y'], v['size'], v['hole'], v['span'][0], v['span'][-1], p['ref'], p['pad'],
                        p['net'], l, '' if p['net'] == v['net'] else ' OTHER NET', ' NEW' if CP.vkey(v) in newv else ' old')
                    (thr if v['span'] == STACK else micro).append(rec)
    print('through vias in SMD pads: %d (new %d)' % (len(thr), sum(' NEW' in r for r in thr)))
    for r in thr:
        print('  ' + r)
    print('microvias in SMD pads: %d (new %d)' % (len(micro), sum(' NEW' in r for r in micro)))
    for r in micro:
        if ' NEW' in r or 'OTHER' in r:
            print('  ' + r)
    dt, dv, _, _ = PS.analyse(M)
    print('dead copper: %d tracks %d vias' % (len(dt), len(dv)))
    for t in dt[:10]:
        print('  dead T %s %s (%.3f,%.3f)-(%.3f,%.3f)' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']))
    for v in dv[:10]:
        print('  dead V %s (%.3f,%.3f)' % (v['net'], v['x'], v['y']))
    oc = C.open_count(C.islands(M))
    print('open %d %s' % (sum(oc.values()), oc))
    print('USB', usb(M))
    addt = P['tracks']
    print('plan: +%d tracks (%.1f mm), -%d tracks; +%d vias, -%d vias' % (
        len(addt), sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in addt), len(P['remove']),
        len(P['vias']), len(P['remove_vias'])))


if __name__ == '__main__':
    main()
