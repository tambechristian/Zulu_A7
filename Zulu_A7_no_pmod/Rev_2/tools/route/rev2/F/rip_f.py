"""rip_f.py -- strategy F rip: keep every piece of old copper that does not clash (exact geometry) with a moved land.

    python rip_f.py            (run from tools/route/rev2/F)  -> rip_f.json, model_f.json, rip_f.log

Starts from the WHOLE board (prep/base_moved.json, pads already moved) and rips only
  a. USB_D_P / USB_D_N inside prep's WINDOW (the pair is hand-routed, B/usb_hand.py; F/usb_f.json is its plan, unchanged);
  b. any track / via of another net closer than the clearance (+0.002) to a moved land on a shared layer
     (through-hole lands: all six layers, and the land is the union of its rect and its drill circle);
  c. any via whose hole is within 0.24 (+0.002) of a moved pad's drill (any net);
  d. any via of the SAME net whose land overlaps a moved SMD land (the move would make it a via-in-pad);
  e. prep rule 3: GND / VCC3V3 tracks ending on an OLD land of a moved pad and plane vias inside an old land;
  f. whole via columns (same net, x, y) of any ripped via.
Everything prep ripped only because of its rule 1 (all of a moved pad's signal net inside the window) is kept.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

STACK = R.STACK
PLANE = {'GND', 'VCC3V3'}
WINDOW = [17.0, 0.0, 46.0, 25.4]
MARGIN = 0.002
PREP = os.path.join(HERE, '..', 'prep')


def pad_layers(p):
    return STACK if p['drill'] else p['layers']


def land_seg(p, s):
    g = C.pad_seg(p, s)
    if p['drill']:
        g = min(g, max(0.0, C.seg_dist(s[0], s[1], s[2], s[3], p['x'], p['y']) - p['drill'] / 2))
    return g


def land_pt(p, x, y):
    g = C.pad_point(p, x, y)
    if p['drill']:
        g = min(g, max(0.0, math.hypot(x - p['x'], y - p['y']) - p['drill'] / 2))
    return g


def vkey(v):
    return (v['net'], round(v['x'], 4), round(v['y'], 4), v['span'][0], v['span'][-1])


def tkey(t):
    return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4),
            round(t['w'], 4))


def classify(B, O, usb=True):
    moved = [(o, n) for o, n in zip(O['pads'], B['pads']) if (o['x'], o['y']) != (n['x'], n['y'])]
    new = [n for _, n in moved]
    old = [o for o, _ in moved]
    inwin = lambda x, y: WINDOW[0] <= x <= WINDOW[2] and WINDOW[1] <= y <= WINDOW[3]  # noqa: E731
    why_t, why_v = {}, {}
    for i, t in enumerate(B['tracks']):
        s = (t['x1'], t['y1'], t['x2'], t['y2'])
        if usb and t['net'] in ('USB_D_P', 'USB_D_N') and (inwin(t['x1'], t['y1']) or inwin(t['x2'], t['y2'])):
            why_t[i] = 'a usb'
            continue
        for p in new:
            if t['layer'] not in pad_layers(p) or (p['net'] and p['net'] == t['net']):
                continue
            g = land_seg(p, s) - t['w'] / 2
            if g < max(R.clearance(t['net'], t['layer']), R.CLEAR) + MARGIN:
                why_t[i] = 'b %.4f from %s.%s' % (g, p['ref'], p['pad'])
                break
        else:
            if t['net'] in PLANE:
                for p in old:
                    if p['net'] == t['net'] and t['layer'] in pad_layers(p) and (
                            C.pad_point(p, t['x1'], t['y1']) <= 0 or C.pad_point(p, t['x2'], t['y2']) <= 0):
                        why_t[i] = 'e on old %s.%s' % (p['ref'], p['pad'])
                        break
    for i, v in enumerate(B['vias']):
        if usb and v['net'] in ('USB_D_P', 'USB_D_N') and inwin(v['x'], v['y']):
            why_v[i] = 'a usb'
            continue
        for p in new:
            if p['drill'] and math.hypot(v['x'] - p['x'], v['y'] - p['y']) - v['hole'] / 2 - p['drill'] / 2 < \
                    R.HOLE_HOLE + MARGIN:
                why_v[i] = 'c hole %s.%s' % (p['ref'], p['pad'])
                break
            sh = set(v['span']) & set(pad_layers(p))
            if not sh:
                continue
            g = land_pt(p, v['x'], v['y']) - v['size'] / 2
            if p['net'] and p['net'] == v['net']:
                if not p['drill'] and g < 0:
                    why_v[i] = 'd in own pad %s.%s' % (p['ref'], p['pad'])
                    break
                continue
            if g < max(max(R.clearance(v['net'], l) for l in sh), R.CLEAR) + MARGIN:
                why_v[i] = 'b %.4f from %s.%s' % (g, p['ref'], p['pad'])
                break
        else:
            if v['net'] in PLANE:
                for p in old:
                    if p['net'] == v['net'] and C.pad_point(p, v['x'], v['y']) <= 0:
                        why_v[i] = 'e in old %s.%s' % (p['ref'], p['pad'])
                        break
    cols = {(B['vias'][i]['net'], round(B['vias'][i]['x'], 4), round(B['vias'][i]['y'], 4)) for i in why_v}
    for i, v in enumerate(B['vias']):
        if i not in why_v and (v['net'], round(v['x'], 4), round(v['y'], 4)) in cols:
            why_v[i] = 'f column'
    return why_t, why_v


def main():
    B = json.load(open(os.path.join(PREP, 'base_moved.json')))
    O = json.load(open(os.path.join(HERE, '..', 'model_base.json')))
    prep = json.load(open(os.path.join(PREP, 'rip.json')))
    why_t, why_v = classify(B, O)
    prep_t = {tkey(t) for t in prep['remove']}
    prep_v = {vkey(v) for v in prep['remove_vias']}
    mine_t = {tkey(B['tracks'][i]) for i in why_t}
    mine_v = {vkey(B['vias'][i]) for i in why_v}
    log = open(os.path.join(HERE, 'rip_f.log'), 'w')
    for i in sorted(why_t):
        t = B['tracks'][i]
        log.write('T %-12s %-12s (%.3f,%.3f)-(%.3f,%.3f) w%.4f  %s%s\n' % (
            t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'], t['w'], why_t[i],
            '' if tkey(t) in prep_t else '  NOT-IN-PREP'))
    for i in sorted(why_v):
        v = B['vias'][i]
        log.write('V %-12s (%.3f,%.3f) %s>%s  %s%s\n' % (v['net'], v['x'], v['y'], v['span'][0], v['span'][-1],
                                                        why_v[i], '' if vkey(v) in prep_v else '  NOT-IN-PREP'))
    kept_t = [t for t in prep['remove'] if tkey(t) not in mine_t]
    kept_v = [v for v in prep['remove_vias'] if vkey(v) not in mine_v]
    for t in kept_t:
        log.write('KEEP T %-12s %-12s (%.3f,%.3f)-(%.3f,%.3f)\n' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'],
                                                                   t['y2']))
    for v in kept_v:
        log.write('KEEP V %-12s (%.3f,%.3f) %s>%s\n' % (v['net'], v['x'], v['y'], v['span'][0], v['span'][-1]))
    log.close()
    rip = {'remove': [B['tracks'][i] for i in sorted(why_t)], 'remove_vias': [B['vias'][i] for i in sorted(why_v)]}
    M = dict(B)
    M['tracks'] = [t for i, t in enumerate(B['tracks']) if i not in why_t]
    M['vias'] = [v for i, v in enumerate(B['vias']) if i not in why_v]
    json.dump(rip, open(os.path.join(HERE, 'rip_f.json'), 'w'), indent=0)
    json.dump(M, open(os.path.join(HERE, 'model_f.json'), 'w'))
    print('rip F: %d tracks, %d vias (prep: %d, %d); kept from prep rip %d tracks, %d vias; not in prep %d tracks, '
          '%d vias' % (len(why_t), len(why_v), len(prep['remove']), len(prep['remove_vias']), len(kept_t), len(kept_v),
                       len(mine_t - prep_t), len(mine_v - prep_v)))
    oc = C.open_count(C.islands(M))
    print('open connections %d on %d nets: %s' % (sum(oc.values()), len(oc), oc))


if __name__ == '__main__':
    main()
