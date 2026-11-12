"""rip_f2.py -- strategy F rip v2: rip_f.py's classification, but a signal / power track that clashes with a moved
land is TRIMMED (the pieces at its two ends that keep the clearance are kept) instead of removed whole.

    python rip_f2.py     -> rip_f2.json {remove, remove_vias, tracks (the kept pieces)}, model_f2a.json, rip_f2.log

GND / VCC3V3 tracks and every via keep rip_f.py's whole-item rule. A kept piece shorter than 0.05 mm is dropped.
Every kept piece is re-checked exactly (route_check geometry) against the moved lands.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rip_f as RF  # noqa: E402

C, R = RF.C, RF.R
STEP = 0.005


def main():
    B = json.load(open(os.path.join(RF.PREP, 'base_moved.json')))
    O = json.load(open(os.path.join(HERE, '..', 'model_base.json')))
    why_t, why_v = RF.classify(B, O)
    new = [n for o, n in zip(O['pads'], B['pads']) if (o['x'], o['y']) != (n['x'], n['y'])]
    pieces = []
    log = open(os.path.join(HERE, 'rip_f2.log'), 'w')

    def ok_seg(t, s):
        for p in new:
            if t['layer'] not in RF.pad_layers(p) or (p['net'] and p['net'] == t['net']):
                continue
            if RF.land_seg(p, s) - t['w'] / 2 < max(R.clearance(t['net'], t['layer']), R.CLEAR) + RF.MARGIN:
                return False
        return True
    for i in sorted(why_t):
        t = B['tracks'][i]
        if not why_t[i].startswith('b') or t['net'] in RF.PLANE:
            continue
        L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
        if L < 0.1:
            continue
        ux, uy = (t['x2'] - t['x1']) / L, (t['y2'] - t['y1']) / L
        for (ax, ay), sgn in (((t['x1'], t['y1']), 1), ((t['x2'], t['y2']), -1)):
            # grow the piece from this end while it stays clear
            a = 0.0
            while a + STEP <= L and ok_seg(t, (ax, ay, ax + sgn * ux * (a + STEP), ay + sgn * uy * (a + STEP))):
                a += STEP
            a = round(a - STEP, 4)               # one step of extra room for the reconnecting track
            if a < 0.05 or a >= L - 0.01:
                continue
            bx, by = round(ax + sgn * ux * a, 4), round(ay + sgn * uy * a, 4)
            pc = dict(t, x1=ax, y1=ay, x2=bx, y2=by)
            assert ok_seg(pc, (pc['x1'], pc['y1'], pc['x2'], pc['y2']))
            pieces.append(pc)
            log.write('PIECE %-12s %-12s (%.3f,%.3f)-(%.3f,%.3f) of %.3f mm w%.3f\n' % (
                t['net'], t['layer'], ax, ay, bx, by, L, t['w']))
    rip = {'remove': [B['tracks'][i] for i in sorted(why_t)], 'remove_vias': [B['vias'][i] for i in sorted(why_v)],
           'tracks': pieces, 'vias': []}
    M = dict(B)
    M['tracks'] = [t for i, t in enumerate(B['tracks']) if i not in why_t] + [dict(p) for p in pieces]
    M['vias'] = [v for i, v in enumerate(B['vias']) if i not in why_v]
    json.dump(rip, open(os.path.join(HERE, 'rip_f2.json'), 'w'), indent=0)
    json.dump(M, open(os.path.join(HERE, 'model_f2a.json'), 'w'))
    log.close()
    oc = C.open_count(C.islands(M))
    print('rip F2: remove %d tracks, %d vias; %d kept pieces; open %d on %d nets' % (
        len(rip['remove']), len(rip['remove_vias']), len(pieces), sum(oc.values()), len(oc)))


if __name__ == '__main__':
    main()
