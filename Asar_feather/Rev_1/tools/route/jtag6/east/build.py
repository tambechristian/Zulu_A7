"""JTAG test points in one 2x3 block at JP3's site (Asar A7 Feather, strategy "east"). READ-ONLY on the board.

    python build.py            model.json (+ route_tdi_tdo.json) -> plan.json, model_moved.json, model_final.json

Deterministic. Inputs: ../model.json and ../comps.json (the fresh model of the board, MD5 9be75ad9) and
route_tdi_tdo.json (tools/router.py output for TDI then TDO on stage A's model, frozen here; `python build.py --stage-a`
writes model_a.json, the model that run used -- see README "Rebuild").

Block (Bottom, 1.27 mm pitch, both parts rotation 90, pad 1 south):
            x 17.20 (JP3)    x 18.47 (JP4)
  y 8.36    GND   JP3-3      VCC3V3 JP4-3
  y 7.09    TMS   JP3-2      TDO    JP4-2
  y 5.82    TCK   JP3-1      TDI    JP4-1
Each column reads like the sibling board's line: GND TMS TCK | VCC3V3 TDO TDI.

Stage A (hand copper, this file):
  * removed: JP4's TDI branch (U2-17 Top run, the through via at (8.3, 2.825), the Bottom run west to the old JP4-1),
    JP4's TDO branch (R91-1 Bottom run west to the old JP4-2), the old JP4-3 VCC3V3 laser, the old JP3-3 GND through
    via (17.475, 7.275) + its 0.025 stub, the TMS tail into the old JP3-2;
  * FT-VCORE: the Top->L4 through via at (17.5, 8.425) (only Top and L4 copper on it) becomes a Top>L2>L3>L4 laser
    stack at the same point, so its Bottom land leaves the new GND pad;
  * VCC1V0 (C86-1 -> C87-1 Bottom feed): the 0.5 run at x 19.1 and its 0.3 / 0.2 neck move east of the new column:
    neck 0.2 straight up to y 6.37, 0.3 out to x 19.45, 0.5 up and back into C86-1 (no piece narrower than before);
  * TCK: the kept L4>L5>Bottom stack at (17.375, 5.175) joins the moved JP3-1 with a 0.67 mm Bottom link;
  * TMS: the kept Bottom run ends at (17.125, 6.575); a 0.52 mm piece joins JP3-2;
  * VCC3V3: L5>Bottom laser 0.30/0.15 between the four upper pads at (17.835, 7.62), 0.2 track to JP4-3;
  * GND: through via 0.35/0.20 at (16.60, 7.885), 0.09 outside JP3-3's copper, 0.25 track to JP3-3.
Stage B (route_tdi_tdo.json): TDI from its L4>L5>Bottom stack at (12.35, 4.1) on L4 to a new stack at (17.1, 4.575),
Bottom into JP4-1; TDO from its L3 run at (13.95, 5.275) on L3, buried to L4 at (17.1, 6.35), stack at (17.85, 6.625),
Bottom into JP4-2.
"""
import copy
import hashlib
import json
import os
import sys

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(HERE)
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
BOT = 'Bottom Layer'
P = 1.27
A, YB = 17.20, 5.82          # JP3 column x, bottom row y
E = A + P                    # JP4 column x


def origins(pcb):
    f = olefile.OleFileIO(pcb)
    out = {}
    for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)):
        if 'PATTERN=' in r:
            kv = dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x)
            out[kv['SOURCEDESIGNATOR']] = (float(kv['X'].replace('mil', '')) * 0.0254,
                                           float(kv['Y'].replace('mil', '')) * 0.0254, float(kv.get('ROTATION', 0)))
    return out


def tkey(t):
    a, b = (round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))
    return (t['net'], t['layer'], round(t['w'], 4)) + tuple(sorted([a, b]))


def vkey(v):
    sp = v['span'] if 'span' in v else S[S.index(v['from']):S.index(v['to']) + 1]
    return (v['net'], round(v['x'], 4), round(v['y'], 4), round(v['hole'], 4), sp[0], sp[-1])


def stage_a(M0):
    newpos = {('JP3', '1'): (A, YB), ('JP3', '2'): (A, YB + P), ('JP3', '3'): (A, YB + 2 * P),
              ('JP4', '1'): (E, YB), ('JP4', '2'): (E, YB + P), ('JP4', '3'): (E, YB + 2 * P)}
    M1 = copy.deepcopy(M0)
    for p in M1['pads']:
        k = (p['ref'], p['pad'])
        if k in newpos:
            p['x'], p['y'] = round(newpos[k][0], 4), round(newpos[k][1], 4)

    def find_t(net, layer, x1, y1, x2, y2):
        k = lambda a, b: (round(a, 3), round(b, 3))
        c = [t for t in M0['tracks'] if t['net'] == net and t['layer'] == layer and
             {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
        assert len(c) == 1, (net, layer, x1, y1, x2, y2, len(c))
        return c[0]

    def find_v(net, x, y, n):
        c = [v for v in M0['vias'] if v['net'] == net and abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3]
        assert len(c) == n, (net, x, y, len(c))
        return c

    rm, rmv = [], []
    # JP4's TDI branch: U2-17 Top run -> through via (8.3, 2.825) -> Bottom run west to the old JP4-1 (4.85, 3.15)
    rm.append(find_t('TDI', 'Top Layer', 8.3, 2.825, 9.85, 2.825))
    rmv += find_v('TDI', 8.3, 2.825, 1)
    rm += [t for t in M0['tracks'] if t['net'] == 'TDI' and t['layer'] == BOT and max(t['x1'], t['x2']) <= 8.3 + 1e-6]
    # JP4's TDO branch: R91-1 Bottom run west to the old JP4-2 (6.12, 3.15)
    rm += [t for t in M0['tracks'] if t['net'] == 'TDO' and t['layer'] == BOT and max(t['x1'], t['x2']) <= 8.75 + 1e-6
           and min(t['y1'], t['y2']) >= 3.3]
    rmv += find_v('VCC3V3', 7.275, 2.775, 1)                  # old JP4-3 L5>Bottom laser
    rmv += find_v('GND', 17.475, 7.275, 1)                    # old JP3-3 through via (it sits on the new JP3-2)
    rm.append(find_t('GND', BOT, 17.475, 7.275, 17.475, 7.3))
    rm.append(find_t('TMS', BOT, 17.125, 6.575, 17.375, 6.45))   # tail into the old JP3-2
    rmv += find_v('FT-VCORE', 17.5, 8.425, 1)                 # through via -> Top>L2>L3>L4 stack, same point
    rm.append(find_t('VCC1V0', BOT, 19.05, 9.25, 19.15, 6.1167))
    rm.append(find_t('VCC1V0', BOT, 19.15, 6.1167, 19.1625, 5.725))
    rm.append(find_t('VCC1V0', BOT, 19.1625, 5.725, 19.1875, 4.9417))
    tracks, vias = [], []

    def T(net, layer, w, x1, y1, x2, y2):
        tracks.append(dict(net=net, layer=layer, w=w, x1=round(x1, 4), y1=round(y1, 4), x2=round(x2, 4), y2=round(y2, 4)))

    def V(net, x, y, size, hole, fr, to):
        vias.append({'net': net, 'x': round(x, 4), 'y': round(y, 4), 'size': size, 'hole': hole, 'from': fr, 'to': to})
    V('FT-VCORE', 17.5, 8.425, 0.30, 0.15, 'Top Layer', 'L2-GND')
    V('FT-VCORE', 17.5, 8.425, 0.30, 0.15, 'L2-GND', 'L3-SIG')
    V('FT-VCORE', 17.5, 8.425, 0.27, 0.15, 'L3-SIG', 'L4-SIG')
    XR, YN = 19.45, YB + 0.55
    T('VCC1V0', BOT, 0.2, 19.1875, 4.9417, 19.19, YN)
    T('VCC1V0', BOT, 0.3, 19.19, YN, XR, YN + XR - 19.19)
    T('VCC1V0', BOT, 0.5, XR, YN + XR - 19.19, XR, 8.85)
    T('VCC1V0', BOT, 0.5, XR, 8.85, 19.05, 9.25)
    T('TCK', BOT, 0.0762, 17.375, 5.175, A, YB)
    T('TMS', BOT, 0.0762, 17.125, 6.575, A, YB + P)
    IX, IY = A + P / 2, YB + 1.5 * P - 0.105     # 0.43 from the VCC3V3 Top>L5 stack at (17.85, 8.05): hole rule 0.24
    V('VCC3V3', IX, IY, 0.30, 0.15, 'L5-VCC3V3', BOT)
    T('VCC3V3', BOT, 0.2, IX, IY, E, YB + 2 * P)
    GX, GY = A - 0.60, YB + 2 * P - 0.475
    V('GND', GX, GY, 0.35, 0.20, 'Top Layer', BOT)
    T('GND', BOT, 0.25, GX, GY, A, YB + 2 * P)
    return M1, dict(remove=rm, remove_vias=rmv, tracks=tracks, vias=vias)


def apply(M1, plan):
    MF = copy.deepcopy(M1)
    rt = {tkey(t) for t in plan['remove']}
    rv = {vkey(v) for v in plan['remove_vias']}
    MF['tracks'] = [t for t in MF['tracks'] if tkey(t) not in rt] + [dict(t) for t in plan['tracks']]
    MF['vias'] = [v for v in MF['vias'] if vkey(v) not in rv] + [
        dict({q: v[q] for q in v if q not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1])
        for v in plan['vias']]
    return MF


def main():
    M0 = json.load(open(os.path.join(J, 'model.json')))
    comps = json.load(open(os.path.join(J, 'comps.json')))
    pcb = os.path.join(J, 'board.PcbDoc')
    print('board copy md5', hashlib.md5(open(pcb, 'rb').read()).hexdigest())
    M1, pa = stage_a(M0)
    if '--stage-a' in sys.argv:
        json.dump(apply(M1, pa), open(os.path.join(HERE, 'model_a.json'), 'w'))
        print('model_a.json written (router input)')
        return
    rb = json.load(open(os.path.join(HERE, 'route_tdi_tdo.json')))
    assert not rb['remove'] and not rb['log'], rb['log']
    plan = {'moves': [], 'remove': pa['remove'], 'remove_vias': pa['remove_vias'],
            'tracks': pa['tracks'] + rb['tracks'], 'vias': pa['vias'] + rb['vias']}
    seen = set()
    for t in plan['remove']:
        assert tkey(t) not in seen
        seen.add(tkey(t))
    base_t, base_v = {tkey(t) for t in M0['tracks']}, {vkey(v) for v in M0['vias']}
    assert all(tkey(t) in base_t for t in plan['remove']), 'a removed track is not on the board'
    assert all(vkey(v) in base_v for v in plan['remove_vias']), 'a removed via is not on the board'
    O = origins(pcb)
    for ref, rot in (('JP3', 90.0), ('JP4', 90.0)):
        ox, oy, orot = O[ref]
        p2 = [p for p in M1['pads'] if p['ref'] == ref and p['pad'] == '2'][0]   # the origin is pad 2's centre
        p1 = [p for p in M1['pads'] if p['ref'] == ref and p['pad'] == '1'][0]
        plan['moves'].append(dict(ref=ref, dx=round(p2['x'] - ox, 4), dy=round(p2['y'] - oy, 4), rotation=rot,
                                  x=round(p2['x'], 4), y=round(p2['y'], 4), pad1=[p1['x'], p1['y']], old_rotation=orot))
    json.dump(M1, open(os.path.join(HERE, 'model_moved.json'), 'w'))
    MF = apply(M1, plan)
    json.dump(MF, open(os.path.join(HERE, 'model_final.json'), 'w'))
    json.dump(plan, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)
    C2 = copy.deepcopy(comps)
    for c in C2['comps']:
        if c['ref'] == 'JP4':
            c['rot'] = 90.0
    json.dump(C2, open(os.path.join(HERE, 'comps_final.json'), 'w'), indent=1)
    print('%d moves, remove %d tracks + %d vias, add %d tracks + %d vias' % (
        len(plan['moves']), len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias'])))
    for m in plan['moves']:
        print('  %-4s (%+.4f, %+.4f) rot %g -> %g: origin (%.4f, %.4f), pad 1 (%.4f, %.4f)' % (
            m['ref'], m['dx'], m['dy'], m['old_rotation'], m['rotation'], m['x'], m['y'], m['pad1'][0], m['pad1'][1]))
    for p in sorted([p for p in M1['pads'] if p['ref'] in ('JP3', 'JP4')], key=lambda p: (-p['y'], p['x'])):
        print('  %s-%s %-7s (%.3f, %.3f)' % (p['ref'], p['pad'], p['net'], p['x'], p['y']))


if __name__ == '__main__':
    main()
