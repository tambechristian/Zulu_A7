"""New X4 (S2B-PH-SM4-TB) and U10 geometry for the router model, plus a conflict report. Read-only on the board."""
import json, math, sys
sys.path.insert(0, "C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools")
import route_conn as C

X4_ORIGIN = (10.8, 19.3)          # body centre; mouth +y, face at y 22.3
U10_ORIGIN = tuple(float(v) for v in (sys.argv[1], sys.argv[2])) if len(sys.argv) > 2 else (5.0, 19.0)
U10_ROT = int(sys.argv[3]) if len(sys.argv) > 3 else 0

def x4_pads():
    ox, oy = X4_ORIGIN
    P = lambda pad, net, dx, dy, w, h: dict(ref='X4', pad=pad, net=net, x=round(ox + dx, 4), y=round(oy + dy, 4), shape='rect',
                                            w=w, h=h, layers=['Top Layer'], drill=0.0, plated=False)
    return [P('1', 'VBATT', 1.0, -4.25, 1.0, 3.5), P('2', 'GND', -1.0, -4.25, 1.0, 3.5),
            P('MP1', '', -3.35, 1.5, 1.5, 3.4), P('MP2', '', 3.35, 1.5, 1.5, 3.4)]

U10_NETS = {'1': 'EE-CS', '2': 'EE-CLK', '3': 'EE-DATA', '4': 'EE-DATA-DO', '5': 'GND', '6': '', '7': '', '8': 'VCC3V3', 'EP': ''}
U10_LOCAL = {str(k): (-0.75 + 0.5 * (k - 1), -1.45) for k in range(1, 5)}
U10_LOCAL.update({str(k): (0.75 - 0.5 * (k - 5), 1.45) for k in range(5, 9)})
U10_LOCAL['EP'] = (0.0, 0.0)

def u10_pads(origin=None, rot=None):
    ox, oy = origin or U10_ORIGIN
    rot = U10_ROT if rot is None else rot
    out = []
    for pad, (lx, ly) in U10_LOCAL.items():
        a = math.radians(rot)
        x = ox + lx * math.cos(a) - ly * math.sin(a); y = oy + lx * math.sin(a) + ly * math.cos(a)
        w, h = (0.25, 0.85) if pad != 'EP' else (1.4, 1.3)
        if rot % 180 == 90:
            w, h = h, w
        out.append(dict(ref='U10', pad=pad, net=U10_NETS[pad], x=round(x, 4), y=round(y, 4), shape='rect', w=w, h=h,
                        layers=['Top Layer'], drill=0.0, plated=False))
    return out

def new_model(M):
    M = json.loads(json.dumps(M))
    M['pads'] = [p for p in M['pads'] if p['ref'] not in ('X4', 'U10')] + x4_pads() + u10_pads()
    return M

def conflicts(M, pads, clear=0.0762):
    """copper of other nets within clear of the given pads (Top-layer pads)"""
    out = []
    for p in pads:
        for i, t in enumerate(M['tracks']):
            if t['layer'] not in p['layers'] or t['net'] == p['net'] and p['net']:
                continue
            d = C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2
            if d < clear:
                out.append(('track', i, p['pad'], t['net'], round(d, 3), t))
        for i, v in enumerate(M['vias']):
            if not set(p['layers']) & set(v['span']) or v['net'] == p['net'] and p['net']:
                continue
            d = C.pad_point(p, v['x'], v['y']) - v['size'] / 2
            if d < clear:
                out.append(('via', i, p['pad'], v['net'], round(d, 3), v))
        for q in M['pads']:
            if q['ref'] in ('X4', 'U10') or not set(p['layers']) & set(q['layers']) or (q['net'] == p['net'] and p['net']):
                continue
            dx = max(abs(p['x'] - q['x']) - (p['w'] + q['w']) / 2, 0); dy = max(abs(p['y'] - q['y']) - (p['h'] + q['h']) / 2, 0)
            d = math.hypot(dx, dy)
            if d < clear + 0.1:
                out.append(('pad', None, p['pad'], q['net'], round(d, 3), (q['ref'], q['pad'])))
    return out

if __name__ == '__main__':
    M0 = json.load(open('model0.json'))
    for name, pads in (('X4', x4_pads()), ('U10', u10_pads())):
        print('==', name, 'conflicts')
        for c in conflicts(M0, pads):
            o = c[5]
            if c[0] == 'track':
                print('  %s pad %-3s vs %-5s %-12s gap %+.3f  %s (%.3f,%.3f)-(%.3f,%.3f) w%.3f' % (name, c[2], c[0], c[3], c[4], o['layer'][:6], o['x1'], o['y1'], o['x2'], o['y2'], o['w']))
            elif c[0] == 'via':
                print('  %s pad %-3s vs %-5s %-12s gap %+.3f  (%.3f,%.3f) %s %.2f' % (name, c[2], c[0], c[3], c[4], o['x'], o['y'], '>'.join(s[:3] for s in o['span']), o['size']))
            else:
                print('  %s pad %-3s vs pad %-12s gap %+.3f  %s' % (name, c[2], c[3], c[4], o))
