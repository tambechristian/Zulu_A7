"""stage A (hand copper): moves, removals, FT-VCORE stack, VCC1V0 detour, TCK/TMS links, VCC3V3 tie.
python stage_a.py A YB  -> model_a.json, plan_a.json"""
import copy
import json
import sys

J = __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))).replace(chr(92), '/') + '/'   # tools/route/jtag6/ (was the session scratchpad)
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
BOT = 'Bottom Layer'
P = 1.27


def run(A, YB, M0, XR=19.45, VY_OFF=0.80):
    E = A + P
    newpos = {('JP3', '1'): (A, YB), ('JP3', '2'): (A, YB + P), ('JP3', '3'): (A, YB + 2 * P),
              ('JP4', '1'): (E, YB), ('JP4', '2'): (E, YB + P), ('JP4', '3'): (E, YB + 2 * P)}
    M1 = copy.deepcopy(M0)
    for p in M1['pads']:
        k = (p['ref'], p['pad'])
        if k in newpos:
            p['x'], p['y'] = round(newpos[k][0], 4), round(newpos[k][1], 4)
    moves = [dict(ref='JP3', dx=round(A - 17.75, 4), dy=round(YB + P - 6.32, 4), rotation=90.0),
             dict(ref='JP4', dx=round(E - 6.12, 4), dy=round(YB + P - 3.15, 4), rotation=90.0)]

    def find_t(net, layer, x1, y1, x2, y2):
        k = lambda a, b: (round(a, 3), round(b, 3))
        c = [t for t in M0['tracks'] if t['net'] == net and t['layer'] == layer and
             {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
        assert len(c) == 1, (net, layer, x1, y1, x2, y2, len(c))
        return c[0]

    def find_v(net, x, y):
        c = [v for v in M0['vias'] if v['net'] == net and abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3]
        assert c, (net, x, y)
        return c

    rm, rmv = [], []
    rm.append(find_t('TDI', 'Top Layer', 8.3, 2.825, 9.85, 2.825))
    rmv += find_v('TDI', 8.3, 2.825)
    for t in M0['tracks']:
        if t['net'] == 'TDI' and t['layer'] == BOT and max(t['x1'], t['x2']) <= 8.3 + 1e-6:
            rm.append(t)
    for t in M0['tracks']:
        if t['net'] == 'TDO' and t['layer'] == BOT and max(t['x1'], t['x2']) <= 8.75 + 1e-6 and min(t['y1'], t['y2']) >= 3.3:
            rm.append(t)
    rmv += find_v('VCC3V3', 7.275, 2.775)
    rmv += find_v('GND', 17.475, 7.275)
    rm.append(find_t('GND', BOT, 17.475, 7.275, 17.475, 7.3))
    rm.append(find_t('TMS', BOT, 17.125, 6.575, 17.375, 6.45))
    rmv += find_v('FT-VCORE', 17.5, 8.425)
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
    YN = YB + 0.55
    T('VCC1V0', BOT, 0.2, 19.1875, 4.9417, 19.19, YN)
    T('VCC1V0', BOT, 0.3, 19.19, YN, XR, YN + XR - 19.19)
    T('VCC1V0', BOT, 0.5, XR, YN + XR - 19.19, XR, 8.85)
    T('VCC1V0', BOT, 0.5, XR, 8.85, 19.05, 9.25)
    T('TCK', BOT, 0.0762, 17.375, 5.175, A, YB)
    T('TMS', BOT, 0.0762, 17.125, 6.575, A, YB + P)
    IX, IY = A + P / 2, YB + 1.5 * P
    V('VCC3V3', IX, IY, 0.30, 0.15, 'L5-VCC3V3', BOT)
    T('VCC3V3', BOT, 0.2, IX, IY, E, YB + 2 * P)
    GX, GY = A - 0.60, YB + 2 * P - 0.475
    V('GND', GX, GY, 0.35, 0.20, 'Top Layer', BOT)
    T('GND', BOT, 0.25, GX, GY, A, YB + 2 * P)
    plan = dict(moves=moves, remove=rm, remove_vias=rmv, tracks=tracks, vias=vias)
    return M1, plan


def apply(M1, plan):
    MF = copy.deepcopy(M1)
    k = lambda t: (t['net'], t['layer'], round(t['w'], 4), tuple(sorted([(round(t['x1'], 4), round(t['y1'], 4)),
                                                                      (round(t['x2'], 4), round(t['y2'], 4))])))
    kv = lambda v: (v['net'], round(v['x'], 4), round(v['y'], 4), round(v['hole'], 4), v['span'][0], v['span'][-1])
    rt = {k(t) for t in plan['remove']}
    rv = {kv(v) for v in plan['remove_vias']}
    MF['tracks'] = [t for t in MF['tracks'] if k(t) not in rt] + [dict(t) for t in plan['tracks']]
    MF['vias'] = [v for v in MF['vias'] if kv(v) not in rv] + [
        dict({q: v[q] for q in v if q not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1])
        for v in plan['vias']]
    return MF


if __name__ == '__main__':
    A, YB = float(sys.argv[1]), float(sys.argv[2])
    M0 = json.load(open(J + 'model.json'))
    M1, plan = run(A, YB, M0)
    MA = apply(M1, plan)
    json.dump(M1, open('model_moved_a.json', 'w'))
    json.dump(MA, open('model_a.json', 'w'))
    json.dump(plan, open('plan_a.json', 'w'), indent=1)
    print('moves', plan['moves'])
    print('remove %d tracks %d vias, add %d tracks %d vias' % (len(plan['remove']), len(plan['remove_vias']),
                                                               len(plan['tracks']), len(plan['vias'])))
